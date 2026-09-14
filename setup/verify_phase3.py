"""
Phase 3 verification: tests ChromaDB semantic search directly.
Sends 6 test questions to the Gemini embedding model, searches ChromaDB,
and verifies the returned tables are semantically correct.
"""
import sys 
sys .path .insert (0 ,".")

from google import genai 
import chromadb 

from config .settings import (
GEMINI_API_KEY ,EMBEDDING_MODEL ,
CHROMA_PERSIST_DIR ,CHROMA_COLLECTION_NAME ,TOP_K ,
)


TEST_CASES =[
{
"question":"Which product sold the most this month?",
"must_contain":["orders","products"],
"reason":"sales volume requires orders + products join",
},
{
"question":"Which city has the most customers?",
"must_contain":["users"],
"reason":"city is a column on the users table",
},
{
"question":"What is the total revenue this month?",
"must_contain":["payments"],
"reason":"revenue = SUM(amount) from payments WHERE status=paid",
},
{
"question":"Which product has the worst reviews and lowest rating?",
"must_contain":["reviews"],
"reason":"rating column lives on the reviews table",
},
{
"question":"Show all pending payments above 5000 rupees",
"must_contain":["payments"],
"reason":"status and amount columns are on the payments table",
},
{
"question":"Which products are running low on stock?",
"must_contain":["products"],
"reason":"stock column lives on the products table",
},
]

client =genai .Client (api_key =GEMINI_API_KEY )
chroma =chromadb .PersistentClient (path =CHROMA_PERSIST_DIR )
collection =chroma .get_collection (name =CHROMA_COLLECTION_NAME )

results_log =[]
print (f"\nTOP_K = {TOP_K } | Embedding model: {EMBEDDING_MODEL }")
print ("="*70 )

for tc in TEST_CASES :
    q =tc ["question"]

    emb =client .models .embed_content (model =EMBEDDING_MODEL ,contents =[q ])
    query_vector =emb .embeddings [0 ].values 


    res =collection .query (query_embeddings =[query_vector ],n_results =TOP_K )
    retrieved_tables =res ["ids"][0 ]
    distances =res ["distances"][0 ]


    passed =all (t in retrieved_tables for t in tc ["must_contain"])
    status ="PASS"if passed else "FAIL"
    results_log .append (passed )

    print (f"\n[{status }] {q }")
    print (f"       Expected: {tc ['must_contain']}  ({tc ['reason']})")
    print (f"       Retrieved (top {TOP_K }):")
    for table ,dist in zip (retrieved_tables ,distances ):
        similarity =1 -dist 
        marker =" <-- EXPECTED"if table in tc ["must_contain"]else ""
        print (f"         {table :<12}  similarity: {similarity :.4f}{marker }")

print ("\n"+"="*70 )
passed_count =sum (results_log )
total =len (results_log )
print (f"\nResult: {passed_count }/{total } tests passed")
if passed_count ==total :
    print ("Phase 3: ALL RETRIEVAL CHECKS PASSED")
else :
    print ("Phase 3: SOME RETRIEVAL CHECKS FAILED")
    print ("  Consider enriching the schema documents and re-running setup_chromadb.py --reset")
