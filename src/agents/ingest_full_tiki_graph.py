import pandas as pd
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

# HuggingFace Local Embedding
from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path=env_path)

URI = os.getenv("URI")
AUTH_USERNAME = os.getenv("AUTH_USERNAME")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")
AUTH = (AUTH_USERNAME, AUTH_PASSWORD)

class TikiEnterpriseGraph:
    def __init__(self, uri, auth):
        self.driver = GraphDatabase.driver(uri, auth=auth)

    def close(self):
        self.driver.close()

    def run_cypher(self, query, parameters=None):
        with self.driver.session() as session:
            session.run(query, parameters)

    def load_parquet(self, folder, file_name):
        path = os.path.join(folder, f"{file_name}.parquet")
        if os.path.exists(path):
            return pd.read_parquet(path).fillna("")
        print(f"Not found : {file_name}.parquet")
        return None

    def prepare_database(self):
        self.run_cypher("MATCH (n) DETACH DELETE n")
        
        nodes = ['Category', 'Coupon', 'Service', 'Seller', 'Reviewer', 'Product', 'Review', 'PriceOffer']
        for node in nodes:
            self.run_cypher(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{node}) REQUIRE n.id IS UNIQUE")
            
        print("[Neo4j] Đang tạo Vector Index cho Review...")
        self.run_cypher("""
        CREATE VECTOR INDEX review_vector IF NOT EXISTS
        FOR (r:Review)
        ON (r.embedding)
        OPTIONS {indexConfig: {
         `vector.dimensions`: 384,
         `vector.similarity_function`: 'cosine'
        }}
        """)

    def ingest_nodes(self, folder):
        
        # 1. Master Data
        self._merge_nodes(folder, 'category', 'Category', 'category_id', 
                          "n.name = row.category_name, n.level = toInteger(row.level), n.path = row.category_path, n.url = row.category_url")
        self._merge_nodes(folder, 'coupon', 'Coupon', 'coupon_id', 
                          "n.code = row.coupon_code, n.title = row.title, n.condition = row.condition, n.expiry = row.expiry")
        self._merge_nodes(folder, 'service', 'Service', 'service_id', 
                          "n.name = row.service_name")
        self._merge_nodes(folder, 'seller', 'Seller', 'seller_id', 
                          "n.name = row.seller_name, n.rating = toFloat(row.seller_rating), n.total_reviews = toInteger(row.total_reviews)")
        self._merge_nodes(folder, 'reviewer', 'Reviewer', 'reviewer_id', 
                          "n.name = row.reviewer_name, n.seniority = row.reviewer_seniority, n.contributions = toInteger(row.reviewer_contributions), n.received_thanks = toInteger(row.reviewer_received_thanks)")

        # 2. Product & Offer
        self._merge_nodes(folder, 'product', 'Product', 'product_id', 
                          "n.name = row.product_name, n.short_desc = row.short_description, n.brand = row.author_brand, n.sold_qty = toInteger(row.sold_quantity), n.review_count = toInteger(row.review_count), n.review_score = toFloat(row.review_score)")
        self._merge_nodes(folder, 'price_offer', 'PriceOffer', 'offer_id', 
                          "n.current_price = toInteger(row.current_price), n.original_price = toInteger(row.original_price), n.discount_percent = toFloat(row.discount_percent), n.crawl_time = row.crawl_time")

        # 3. Review (VECTOR EMBEDDING)
        print("\n[BẮT ĐẦU NẠP VÀ NHÚNG VECTOR BẰNG LOCAL CPU/GPU]")
        # --- TỐI ƯU 1: GIẢM BATCH_SIZE CỦA NEO4J XUỐNG 250 ĐỂ TRÁNH TRÀN RAM ---
        self._merge_nodes(folder, 'review', 'Review', 'review_id', 
                          "n.content = row.review_content, n.rating = toFloat(row.rating_score), n.thank_count = toInteger(row.thank_count), n.review_time = row.review_time, n.usage_duration = row.usage_duration",
                          embed_col='review_content', batch_size=250)

    def _merge_nodes(self, folder, file_name, label, id_col, set_properties, batch_size=10000, embed_col=None):
        df = self.load_parquet(folder, file_name)
        if df is not None:
            records = df.to_dict('records')
            total = len(records)
            
            embeddings_model = None
            if embed_col:
                print("   -> Đang tải mô hình NLP về máy (Đã được cấu hình tăng tốc)...")
                # --- TỐI ƯU 2: ÉP HUGGINGFACE CHẠY LÔ 128 ĐỂ TĂNG TỐC ĐỘ ĐỌC ---
                # (Sẽ tự động dùng GPU nếu máy bạn có cài đặt CUDA)
                embeddings_model = HuggingFaceEmbeddings(
                    model_name="paraphrase-multilingual-MiniLM-L12-v2",
                    encode_kwargs={'batch_size': 128} 
                )
                
                query = f"""
                UNWIND $rows AS row
                MERGE (n:{label} {{id: toString(row.{id_col})}})
                SET {set_properties}, n.embedding = row.embedding
                """
            else:
                query = f"""
                UNWIND $rows AS row
                MERGE (n:{label} {{id: toString(row.{id_col})}})
                SET {set_properties}
                """
            
            for i in range(0, total, batch_size):
                batch = records[i:i + batch_size]
                
                if embed_col and embeddings_model:
                    print(f"  [Local AI] Đang tính toán Vector cho {len(batch)} đánh giá...")
                    texts_to_embed = [str(row.get(embed_col, "")) for row in batch]
                    # HuggingFace sẽ nhúng 128 câu cùng lúc nhờ encode_kwargs ở trên
                    vectors = embeddings_model.embed_documents(texts_to_embed)
                    
                    for j, row in enumerate(batch):
                        row['embedding'] = vectors[j]

                # Gửi gói dữ liệu nhỏ (250 dòng) vào Neo4j, an toàn tuyệt đối cho RAM
                self.run_cypher(query, {"rows": batch})
                print(f"+ Đã lưu vào Neo4j lô: {i} -> {i + len(batch)} / {total}")

    def ingest_relationships(self, folder):
        self._create_relation(folder, 'category', 'Category', 'category_id', 'Category', 'parent_category_id', 'THUOC_DANH_MUC_CHA')
        self._create_relation(folder, 'product', 'Product', 'product_id', 'Category', 'category_id', 'THUOC_DANH_MUC')
        self._create_relation(folder, 'product', 'Seller', 'seller_id', 'Product', 'product_id', 'BAN')
        self._create_relation(folder, 'review', 'Review', 'review_id', 'Product', 'product_id', 'DANH_GIA_CHO')
        self._create_relation(folder, 'review', 'Reviewer', 'reviewer_id', 'Review', 'review_id', 'VIET')
        self._create_relation(folder, 'price_offer', 'PriceOffer', 'offer_id', 'Product', 'product_id', 'AP_DUNG_CHO_SAN_PHAM')

        batch_size = 10000
        
        df_offer_coupon = self.load_parquet(folder, 'offer_coupon')
        if df_offer_coupon is not None:
            records = df_offer_coupon.to_dict('records')
            total = len(records)
            query = """
            UNWIND $rows AS row
            MATCH (o:PriceOffer {id: toString(row.offer_id)}) 
            MATCH (c:Coupon {id: toString(row.coupon_id)})
            MERGE (o)-[:AP_DUNG_MA]->(c)
            """
            for i in range(0, total, batch_size):
                batch = records[i:i + batch_size]
                self.run_cypher(query, {"rows": batch})
                print(f"+ Creating a connection [:AP_DUNG_MA]: {i} -> {i + len(batch)} / {total}")

        df_offer_service = self.load_parquet(folder, 'offer_service')
        if df_offer_service is not None:
            records = df_offer_service.to_dict('records')
            total = len(records)
            query = """
            UNWIND $rows AS row
            MATCH (o:PriceOffer {id: toString(row.offer_id)})
            MATCH (s:Service {id: toString(row.service_id)})
            MERGE (o)-[:KEM_DICH_VU]->(s)
            """
            for i in range(0, total, batch_size):
                batch = records[i:i + batch_size]
                self.run_cypher(query, {"rows": batch})
                print(f"+ Creating a connection [:KEM_DICH_VU]: {i} -> {i + len(batch)} / {total}")

    def _create_relation(self, folder, source_file, label1, key1, label2, key2, rel_name, batch_size=10000):
        df = self.load_parquet(folder, source_file)
        if df is not None:
            records = df.to_dict('records')
            total = len(records)
            
            query = f"""
            UNWIND $rows AS row
            WITH row WHERE row.{key1} IS NOT NULL AND row.{key2} IS NOT NULL 
                       AND toString(row.{key1}) <> "" AND toString(row.{key2}) <> ""
            MATCH (a:{label1} {{id: toString(row.{key1})}})
            MATCH (b:{label2} {{id: toString(row.{key2})}})
            MERGE (a)-[:{rel_name}]->(b)
            """
            
            for i in range(0, total, batch_size):
                batch = records[i:i + batch_size]
                self.run_cypher(query, {"rows": batch})
                print(f"+ Creating a connection [:{rel_name}]: {i} -> {i + len(batch)} / {total}")
                
if __name__ == "__main__":
    DATA_FOLDER = os.path.join(BASE_DIR, 'data')
    
    graph_db = TikiEnterpriseGraph(URI, AUTH)
    graph_db.prepare_database()
    graph_db.ingest_nodes(DATA_FOLDER)
    graph_db.ingest_relationships(DATA_FOLDER)
    graph_db.close()

