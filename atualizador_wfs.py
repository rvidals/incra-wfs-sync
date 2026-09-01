import psycopg2
from psycopg2 import sql, extras
import requests
import pandas as pd
from datetime import datetime
import logging
import json
import os
import sys
from typing import Dict, List, Tuple
import traceback
import time
import xml.etree.ElementTree as ET
import re

# Configuração de logging
def setup_logging():
    """Configura o sistema de logging"""
    os.makedirs('logs', exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler('logs/atualizacao.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


class WFSDataFetcher:
    """Classe para buscar dados do serviço WFS"""
    
    def __init__(self, config):
        self.wfs_url = config['url']
        self.type_name = config['type_name']
        self.srsname = config.get('srsname', 'EPSG:4326')
        self.max_features = config.get('max_features', 50000)
        
    def fetch_data(self) -> pd.DataFrame:
        """Busca dados do WFS em formato XML e retorna como DataFrame"""
        logger.info(f"Buscando dados do WFS: {self.type_name}")
        
        params = {
            'SERVICE': 'WFS',
            'VERSION': '1.1.0',
            'REQUEST': 'GetFeature',
            'TYPENAME': self.type_name,
            'SRSNAME': self.srsname,
            'MAXFEATURES': self.max_features
        }
        
        try:
            start_time = time.time()
            logger.info("Obtendo dados em formato XML...")
            
            response = requests.get(self.wfs_url, params=params, timeout=300)
            response.raise_for_status()
            
            elapsed_time = time.time() - start_time
            logger.info(f"Requisição concluída em {elapsed_time:.2f} segundos")
            logger.info(f"Tamanho da resposta: {len(response.text):,} bytes")
            
            df = self._parse_xml(response.text)
            
            if df.empty:
                logger.warning("Nenhum dado extraído do XML")
            else:
                logger.info(f"Carregados {len(df):,} registros do WFS")
                logger.info(f"Colunas encontradas: {list(df.columns)}")
                
                if len(df) > 0:
                    logger.info("Amostra dos dados (primeiro registro):")
                    for col in df.columns[:15]:
                        val = df[col].iloc[0]
                        if pd.notna(val):
                            logger.info(f"  {col}: {str(val)[:100]}")
            
            return df
            
        except requests.exceptions.Timeout:
            logger.error("Timeout na requisição WFS")
            return pd.DataFrame()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição WFS: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def _parse_xml(self, xml_content: str) -> pd.DataFrame:
        """Parse dados XML do WFS"""
        try:
            if xml_content.startswith('\ufeff'):
                xml_content = xml_content[1:]
            
            root = ET.fromstring(xml_content)
            
            namespaces = {
                'wfs': 'http://www.opengis.net/wfs',
                'gml': 'http://www.opengis.net/gml',
                'ms': 'http://www.omsug.ca/osgis2004',
                'ogc': 'http://www.opengis.net/ogc'
            }
            
            features = []
            
            for member in root.findall('.//wfs:featureMember', namespaces):
                for feature in member:
                    features.append(feature)
            
            if not features:
                for member in root.findall('.//featureMember'):
                    for feature in member:
                        features.append(feature)
            
            if not features:
                feature_name = self.type_name.split(':')[-1]
                for elem in root.findall(f'.//{feature_name}'):
                    features.append(elem)
                if not features:
                    for elem in root.findall(f'.//ms:{feature_name}', namespaces):
                        features.append(elem)
            
            logger.info(f"Encontradas {len(features)} features no XML")
            
            if not features:
                logger.warning("Nenhuma feature encontrada no XML")
                return pd.DataFrame()
            
            rows = []
            
            for idx, feature in enumerate(features):
                row = {}
                geom_wkt = None
                
                for elem in feature:
                    tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    
                    # Extrair geometria
                    if tag_name == 'msGeometry' or 'geometry' in tag_name.lower():
                        geom_wkt = self._extract_geometry(elem, namespaces)
                        if geom_wkt:
                            row['geom'] = geom_wkt
                        continue
                    
                    # Ignorar outros elementos de geometria
                    if tag_name in ['boundedBy', 'Envelope', 'lowerCorner', 
                                   'upperCorner', 'Polygon', 'exterior', 'LinearRing', 'posList']:
                        continue
                    
                    # Extrair atributos normais
                    if elem.text and elem.text.strip():
                        row[tag_name] = elem.text.strip()
                
                if row:
                    rows.append(row)
                
                if (idx + 1) % 1000 == 0:
                    logger.info(f"Processados {idx + 1} registros...")
            
            if not rows:
                logger.warning("Nenhum dado extraído das features")
                return pd.DataFrame()
            
            df = pd.DataFrame(rows)
            logger.info(f"DataFrame criado com {len(df)} linhas e {len(df.columns)} colunas")
            
            # Converter tipos
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].str.strip()
                    df[col] = df[col].replace('', None)
            
            # Converter gid para string SEM formatação científica
            if 'gid' in df.columns:
                # Remover .0 e converter para string
                df['gid'] = df['gid'].astype(str).str.replace(r'\.0$', '', regex=True)
                logger.info(f"gid convertido para string: {df['gid'].iloc[0]}...")
            
            # NÃO converter colunas para numérico - manter como string para consistência com varchar no banco
            # Remover conversões numéricas desnecessárias
            
            # Converter area_ha (pode vir com formato brasileiro: 759.123.700)
            if 'area_ha' in df.columns:
                try:
                    # Remover pontos de milhar e converter vírgula para ponto
                    df['area_ha'] = df['area_ha'].astype(str).str.replace('.', '', regex=False)
                    df['area_ha'] = df['area_ha'].str.replace(',', '.')
                    df['area_ha'] = pd.to_numeric(df['area_ha'], errors='coerce')
                except Exception as e:
                    logger.warning(f"Não foi possível converter area_ha: {e}")
            
            if 'area_re_ha' in df.columns:
                try:
                    df['area_re_ha'] = df['area_re_ha'].astype(str).str.replace('.', '', regex=False)
                    df['area_re_ha'] = df['area_re_ha'].str.replace(',', '.')
                    df['area_re_ha'] = pd.to_numeric(df['area_re_ha'], errors='coerce')
                except Exception as e:
                    logger.warning(f"Não foi possível converter area_re_ha: {e}")
            
            # Converter data
            if 'data_certi' in df.columns:
                try:
                    df['data_certi'] = pd.to_datetime(df['data_certi'], errors='coerce')
                except Exception as e:
                    logger.warning(f"Não foi possível converter data_certi: {e}")
            
            return df
            
        except ET.ParseError as e:
            logger.error(f"Erro ao parsear XML: {e}")
            debug_file = f"logs/erro_xml_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(xml_content[:2000])
            logger.info(f"XML salvo em {debug_file} para debug")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Erro ao processar XML: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def _extract_geometry(self, elem, namespaces) -> str:
        """Extrai geometria como WKT - CORRIGIDO para inverter Lat/Lon para Lon/Lat"""
        try:
            # Buscar posList
            pos_list = elem.find('.//gml:posList', namespaces)
            if pos_list is not None and pos_list.text:
                coords = pos_list.text.strip().split()
                if len(coords) >= 6:  # Mínimo para um polígono
                    # Converter para WKT Polygon INVERTENDO LAT/LON
                    wkt = "POLYGON (("
                    points = []
                    for i in range(0, len(coords), 2):
                        if i + 1 < len(coords):
                            # INVERTER: longitude primeiro, depois latitude
                            # WFS 1.1.0 retorna lat lon, PostGIS espera lon lat
                            lat = coords[i]
                            lon = coords[i+1]
                            points.append(f"{lon} {lat}")
                    # Fechar o polígono
                    if points:
                        points.append(points[0])  # Fechar anel
                        wkt += ", ".join(points)
                    wkt += "))"
                    logger.debug(f"Geometria extraída (posList): {wkt[:80]}...")
                    return wkt
            
            # Buscar coordinates
            coords_elem = elem.find('.//gml:coordinates', namespaces)
            if coords_elem is not None and coords_elem.text:
                coords_text = coords_elem.text.strip()
                # Formato: "x1,y1 x2,y2 x3,y3 ..." - também INVERTER
                coords = []
                for pair in coords_text.split():
                    if ',' in pair:
                        x, y = pair.split(',')
                        # INVERTER: longitude (y) primeiro, latitude (x) depois
                        coords.append(f"{y} {x}")
                if len(coords) >= 3:
                    coords.append(coords[0])  # Fechar anel
                    wkt = f"POLYGON (({', '.join(coords)}))"
                    logger.debug(f"Geometria extraída (coordinates): {wkt[:80]}...")
                    return wkt
            
            logger.warning("Nenhuma geometria encontrada no elemento")
            return None
        except Exception as e:
            logger.error(f"Erro ao extrair geometria: {e}")
            return None


class PostgresUpdater:
    """Classe para gerenciar atualizações no PostgreSQL"""
    
    def __init__(self, config):
        self.db_config = config['database']
        self.schema = config['table']['schema']
        self.table_name = config['table']['name']
        self.pk_columns = config['table']['primary_key']
        self.batch_size = config.get('update', {}).get('batch_size', 1000)
        self.connection = None
        self.cursor = None
        
    def connect(self) -> bool:
        """Estabelece conexão com o PostgreSQL"""
        try:
            logger.info(f"Conectando ao PostgreSQL em {self.db_config['host']}:{self.db_config['port']}")
            self.connection = psycopg2.connect(**self.db_config)
            self.cursor = self.connection.cursor()
            
            self.cursor.execute("SELECT version()")
            version = self.cursor.fetchone()[0]
            logger.info(f"PostgreSQL versão: {version[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar ao PostgreSQL: {e}")
            return False
    
    def disconnect(self):
        """Fecha a conexão"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Conexão com PostgreSQL fechada")
    
    def table_exists(self) -> bool:
        """Verifica se a tabela existe no schema"""
        query = sql.SQL("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name = %s
            )
        """)
        self.cursor.execute(query, (self.schema, self.table_name))
        return self.cursor.fetchone()[0]
    
    def get_table_columns(self) -> List[str]:
        """Obtém lista de colunas da tabela"""
        query = sql.SQL("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s 
            AND table_name = %s
            ORDER BY ordinal_position
        """)
        self.cursor.execute(query, (self.schema, self.table_name))
        return [row[0] for row in self.cursor.fetchall()]
    
    def get_last_fid(self) -> int:
        """Obtém o último valor de fid da tabela"""
        try:
            self.cursor.execute(f"SELECT COALESCE(MAX(fid), 0) FROM {self.schema}.{self.table_name}")
            result = self.cursor.fetchone()[0]
            logger.info(f"Último fid encontrado: {result}")
            return result
        except Exception as e:
            logger.warning(f"Erro ao buscar último fid: {e}. Usando 0 como padrão.")
            return 0
    
    def ensure_primary_key(self) -> bool:
        """Verifica e cria PRIMARY KEY se não existir"""
        try:
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.table_constraints 
                    WHERE constraint_type = 'PRIMARY KEY'
                    AND table_schema = %s
                    AND table_name = %s
                )
            """, (self.schema, self.table_name))
            
            has_pk = self.cursor.fetchone()[0]
            
            if has_pk:
                logger.info("Tabela já possui PRIMARY KEY")
                return True
            
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_schema = %s 
                    AND table_name = %s 
                    AND column_name = 'gid'
                )
            """, (self.schema, self.table_name))
            
            has_gid = self.cursor.fetchone()[0]
            
            if not has_gid:
                logger.warning("Coluna 'gid' não encontrada. Adicionando...")
                self.cursor.execute(f"""
                    ALTER TABLE {self.schema}.{self.table_name} 
                    ADD COLUMN gid VARCHAR
                """)
                self.connection.commit()
                logger.info("Coluna 'gid' adicionada")
            
            logger.info("Criando PRIMARY KEY na coluna gid...")
            self.cursor.execute(f"""
                ALTER TABLE {self.schema}.{self.table_name} 
                ADD PRIMARY KEY (gid)
            """)
            self.connection.commit()
            logger.info("PRIMARY KEY criada com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao criar PRIMARY KEY: {e}")
            self.connection.rollback()
            return False
    
    def get_current_data(self) -> pd.DataFrame:
        """Obtém todos os dados atuais da tabela SEM depender de sqlalchemy"""
        logger.info("Carregando dados atuais da tabela...")
        
        # Usar cursor para ler dados e construir DataFrame
        query = f'SELECT * FROM {self.schema}.{self.table_name}'
        self.cursor.execute(query)
        
        # Obter nomes das colunas
        column_names = [desc[0] for desc in self.cursor.description]
        
        # Ler todas as linhas
        rows = self.cursor.fetchall()
        
        # Construir DataFrame
        df = pd.DataFrame(rows, columns=column_names)
        
        # Converter gid para string para comparação
        if 'gid' in df.columns:
            df['gid'] = df['gid'].astype(str).str.strip()
            logger.info(f"gid convertido para string para comparação")
        
        logger.info(f"Carregados {len(df):,} registros da tabela")
        return df
    
    def identify_changes(self, current_df: pd.DataFrame, 
                     new_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Identifica registros novos e atualizados usando comparação de chaves
        CORRIGIDO para lidar com múltiplos registros por GID
        """
        
        # Caso 1: Tabela vazia
        if current_df.empty:
            logger.info("Tabela vazia - todos os registros serão INSERIDOS")
            return new_df, pd.DataFrame()
        
        # Caso 2: Sem dados novos
        if new_df.empty:
            logger.warning("Nenhum dado novo para processar")
            return pd.DataFrame(), pd.DataFrame()
        
        # Verificar se gid existe em ambos
        if 'gid' not in current_df.columns or 'gid' not in new_df.columns:
            logger.error("Coluna 'gid' não encontrada em um dos DataFrames!")
            return pd.DataFrame(), pd.DataFrame()
        
        # Converter gid para string
        current_df['gid'] = current_df['gid'].astype(str).str.strip()
        new_df['gid'] = new_df['gid'].astype(str).str.strip()
        
        # REMOVER DUPLICATAS: manter apenas primeiro registro de cada GID
        new_df_unique = new_df.drop_duplicates(subset=['gid'], keep='first')
        current_df_unique = current_df.drop_duplicates(subset=['gid'], keep='first')
        
        logger.info(f"GIDs únicos no WFS: {len(new_df_unique)} (de {len(new_df)} total)")
        logger.info(f"GIDs únicos na tabela: {len(current_df_unique)} (de {len(current_df)} total)")
        
        # Criar conjuntos de gids
        current_gids = set(current_df_unique['gid'].tolist())
        new_gids = set(new_df_unique['gid'].tolist())
        
        logger.info(f"GIDs na tabela: {len(current_gids)}")
        logger.info(f"GIDs no WFS: {len(new_gids)}")
        
        # Encontrar GIDs para INSERT (novos)
        gids_to_insert = new_gids - current_gids
        logger.info(f"🔵 GIDs NOVOS (INSERT): {len(gids_to_insert)}")
        if len(gids_to_insert) <= 10:
            logger.info(f"   GIDs: {sorted(gids_to_insert)}")
        
        # Encontrar GIDs para UPDATE (existem em ambos)
        gids_to_update = current_gids & new_gids
        logger.info(f"🟡 GIDs EXISTENTES (UPDATE potencial): {len(gids_to_update)}")
        
        # Filtrar DataFrames (usando únicos)
        to_insert = new_df_unique[new_df_unique['gid'].isin(gids_to_insert)]
        to_update_potential = new_df_unique[new_df_unique['gid'].isin(gids_to_update)]
        
        # Verificar quais realmente mudaram
        if not to_update_potential.empty:
            logger.info("Verificando quais registros realmente mudaram...")
            current_dict = {row['gid']: row for _, row in current_df_unique.iterrows()}
            
            registros_mudaram = []
            for _, new_row in to_update_potential.iterrows():
                gid = new_row['gid']
                current_row = current_dict.get(gid)
                
                if current_row is None:
                    continue
                
                # Comparar colunas (exceto fid e gid)
                changed = False
                colunas_mudaram = []
                
                for col in new_row.index:
                    if col in ['fid', 'gid']:  # Apenas excluir PK
                        continue
                    if col not in current_row.index:
                        continue
                    
                    # TRATAMENTO ESPECIAL PARA GEOMETRIA
                    if col == 'geom':
                        continue
                    
                    # TRATAMENTO ESPECIAL PARA AREA_RE_HA E AREA_HA
                    if col in ['area_re_ha', 'area_ha']:
                        val_new = new_row[col] if pd.notna(new_row[col]) else ''
                        val_current = current_row[col] if pd.notna(current_row[col]) else ''
                        
                        # Normalizar para comparação numérica
                        try:
                            val_new_str = str(val_new).replace('.', '').replace(',', '.')
                            val_new_float = float(val_new_str) if val_new_str else None
                            
                            val_current_str = str(val_current).replace('.', '').replace(',', '.')
                            val_current_float = float(val_current_str) if val_current_str else None

                            # Adicione dentro do tratamento do area_re_ha:
                            # logger.info(f"  DEBUG GID {gid}: area_re_ha WFS='{val_new}' | DB='{val_current}' | new_float={val_new_float} | cur_float={val_current_float}")
                            
                            # Comparar com tolerância
                            if val_new_float is not None and val_current_float is not None:
                                if abs(val_new_float - val_current_float) > 0.01:
                                    changed = True
                                    colunas_mudaram.append(col)
                            elif val_new_float != val_current_float:
                                changed = True
                                colunas_mudaram.append(col)
                        except:
                            val_new_norm = str(val_new).replace('.', '').replace(',', '').strip()
                            val_current_norm = str(val_current).replace('.', '').replace(',', '').strip()
                            if val_new_norm != val_current_norm:
                                changed = True
                                colunas_mudaram.append(col)
                        
                        continue
                    
                    # Comparação normal para outras colunas
                    val_new = str(new_row[col]) if pd.notna(new_row[col]) else ''
                    val_current = str(current_row[col]) if pd.notna(current_row[col]) else ''
                    
                    val_new = val_new.strip()
                    val_current = val_current.strip()
                    
                    if val_new != val_current:
                        changed = True
                        colunas_mudaram.append(col)
                
                # Se alguma coluna de atributo mudou, marcar para update
                if changed:
                    registros_mudaram.append(new_row)
                    logger.info(f"  GID {gid}: mudou em {colunas_mudaram}")
            
            to_update = pd.DataFrame(registros_mudaram) if registros_mudaram else pd.DataFrame()
        else:
            to_update = pd.DataFrame()
        
        logger.info(f"🟢 REGISTROS PARA UPDATE (efetivos): {len(to_update)}")
        
        # GIDs que existem na tabela mas não no WFS (não deletamos)
        gids_to_delete = current_gids - new_gids
        if gids_to_delete:
            logger.info(f"🔴 GIDs APENAS NA TABELA (não deletados): {len(gids_to_delete)}")
            if len(gids_to_delete) <= 10:
                logger.info(f"   GIDs: {sorted(gids_to_delete)}")
        
        return to_insert, to_update
    
    def _format_value_for_sql(self, val, col_name=None) -> str:
        """Formata um valor para SQL"""
        if pd.isna(val):
            return 'NULL'
        
        if col_name == 'geom' and val and isinstance(val, str) and val.startswith('POLYGON'):
            # Geometria - usar ST_GeomFromText
            # IMPORTANTE: garantir que as coordenadas estão em lon/lat
            return f"ST_GeomFromText('{val}', 4326)"
        
        if isinstance(val, (pd.Timestamp, datetime)):
            return f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'"
        
        if isinstance(val, str):
            val_escaped = val.replace("'", "''")
            return f"'{val_escaped}'"
        
        if isinstance(val, (int, float)):
            return str(val)
        
        return f"'{str(val)}'"
    
    def upsert_data(self, df_insert: pd.DataFrame, df_update: pd.DataFrame) -> Dict:
        """Realiza UPSERT no PostgreSQL"""
        stats = {
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'message': 'SUCESSO'
        }
        
        try:
            table_columns = self.get_table_columns()
            logger.info(f"Colunas da tabela: {table_columns}")
            
            # ... código do INSERT (manter igual) ...
            
            # 2. ATUALIZAR registros existentes
            if not df_update.empty:
                logger.info(f"Atualizando {len(df_update):,} registros...")
                
                # Filtrar colunas
                available_cols = [col for col in df_update.columns if col in table_columns]
                df_update_filtered = df_update[available_cols]
                
                total_updated = 0
                for idx, row in df_update_filtered.iterrows():
                    set_parts = []
                    values = []
                    for col in row.index:
                        if col not in ['gid', 'fid', 'geom']:  # NÃO atualizar geom
                            val = row[col]
                            if pd.isna(val):
                                set_parts.append(f'"{col}" = NULL')
                            elif isinstance(val, (pd.Timestamp, datetime)):
                                set_parts.append(f'"{col}" = %s')
                                values.append(val)
                            else:
                                set_parts.append(f'"{col}" = %s')
                                values.append(val)
                    
                    gid_val = row['gid']
                    values.append(gid_val)
                    
                    update_query = f"""
                        UPDATE {self.schema}.{self.table_name}
                        SET {', '.join(set_parts)}
                        WHERE "gid" = %s
                    """
                    
                    self.cursor.execute(update_query, tuple(values))
                    total_updated += 1
                    
                    if (idx + 1) % 50 == 0:
                        logger.info(f"Atualizados {total_updated:,} de {len(df_update_filtered):,} registros")
                
                stats['updated'] = total_updated
            
            # Commit
            self.connection.commit()
            logger.info("Transação commitada com sucesso!")
            
        except Exception as e:
            self.connection.rollback()
            stats['errors'] = 1
            stats['message'] = f'ERRO: {str(e)}'
            logger.error(f"Erro no UPSERT: {e}")
            logger.error(traceback.format_exc())
            raise
        
        return stats


def main():
    """Função principal"""
    try:
        logger.info("="*60)
        logger.info("INICIANDO ATUALIZAÇÃO AUTOMÁTICA")
        logger.info(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        
        config_path = 'config.json'
        if not os.path.exists(config_path):
            logger.error(f"Arquivo de configuração não encontrado: {config_path}")
            sys.exit(1)
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        logger.info("Configuração carregada com sucesso")
        logger.info(f"Tabela destino: {config['table']['schema']}.{config['table']['name']}")
        
        fetcher = WFSDataFetcher(config['wfs'])
        new_data = fetcher.fetch_data()
        
        if new_data.empty:
            logger.warning("Nenhum dado obtido do WFS. Operação cancelada.")
            return
        
        updater = PostgresUpdater(config)
        if not updater.connect():
            logger.error("Falha na conexão com PostgreSQL. Operação cancelada.")
            return
        
        try:
            if not updater.table_exists():
                logger.error(f"Tabela {config['table']['schema']}.{config['table']['name']} não existe!")
                return
            
            if not updater.ensure_primary_key():
                logger.error("Não foi possível criar PRIMARY KEY. Operação cancelada.")
                return
            
            # Buscar dados atuais
            current_data = updater.get_current_data()
            
            # Identificar mudanças
            to_insert, to_update = updater.identify_changes(current_data, new_data)
            
            # Executar UPSERT
            if not to_insert.empty or not to_update.empty:
                # Limpar dados duplicados ANTES de inserir
                if not to_insert.empty:
                    logger.info("⚠️ Verificando duplicatas antes de inserir...")
                    # Verificar se algum gid já existe (por segurança)
                    existing_gids = set(current_data['gid'].tolist())
                    to_insert = to_insert[~to_insert['gid'].isin(existing_gids)]
                    logger.info(f"Após verificação, {len(to_insert)} registros para inserir")
                
                stats = updater.upsert_data(to_insert, to_update)
                
                logger.info("="*60)
                logger.info("OPERAÇÃO CONCLUÍDA")
                logger.info(f"✅ Inseridos: {stats['inserted']:,}")
                logger.info(f"✅ Atualizados: {stats['updated']:,}")
                logger.info(f"✅ Status: {stats['message']}")
                logger.info("="*60)
            else:
                logger.info("✅ Nenhuma alteração detectada. Tabela já está atualizada!")
            
        finally:
            updater.disconnect()
        
    except Exception as e:
        logger.error(f"❌ Erro fatal na execução: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()