import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, request

# LangChain setup
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_together import ChatTogether
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate

import tempfile
import traceback

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent / ".env")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

# Config
INDEX_NAME = "policy-index"
DATA_DIR = "data/"
PINECONE_REGION = "us-east-1"

app = Flask(__name__)

# Embeddings & LLM
embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
llm = ChatTogether(
    model="mistralai/Mixtral-8x7B-Instruct-v0.1",
    api_key=TOGETHER_API_KEY,
    temperature=0.3,
    max_tokens=512,
)

# Pinecone setup
pc = Pinecone(api_key=PINECONE_API_KEY)
if INDEX_NAME not in [i.name for i in pc.list_indexes()]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=64)
    docs = []
    for file in Path(DATA_DIR).glob("*.pdf"):
        loader = PyPDFLoader(str(file))
        docs.extend(loader.load())
    chunks = splitter.split_documents(docs)

    pc.create_index(
        name=INDEX_NAME,
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=PINECONE_REGION)
    )
    PineconeVectorStore.from_documents(chunks, embedding=embedding, index_name=INDEX_NAME)

vectorstore = PineconeVectorStore.from_existing_index(index_name=INDEX_NAME, embedding=embedding)
retriever = vectorstore.as_retriever()

# Prompts
parse_prompt = ChatPromptTemplate.from_template("""
Extract the following from the query:
- Age
- Gender
- Procedure
- Location
- Policy Duration

Query: {input}
Context: {context}
""")

decision_prompt = ChatPromptTemplate.from_template("""
You are a policy decision assistant.

Using these extracted details:
{parsed}

And the policy clauses below:
{context}

Respond in 2–3 sentences explaining whether the procedure is covered.
Avoid JSON formatting or labels. Just write a plain, readable explanation.
""")

parser_chain = create_stuff_documents_chain(llm, parse_prompt)
qa_chain = create_stuff_documents_chain(llm, decision_prompt)
rag_chain = create_retrieval_chain(retriever, qa_chain)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    try:
        query = request.form.get("query", "").strip()
        uploaded_files = request.files.getlist("files")

        file_texts = []

        for file in uploaded_files:
            filename = file.filename
            if not filename:
                continue

            suffix = Path(filename).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False) as temp:
                file.save(temp.name)

                if suffix == ".pdf":
                    loader = PyPDFLoader(temp.name)
                    docs = loader.load()
                    file_texts.extend([doc.page_content for doc in docs])
                # Add DOCX or image processing here if needed later

        context_text = "\n".join(file_texts)

        parsed_output = parser_chain.invoke({
            "input": query,
            "context": ""
        })

        final_output = rag_chain.invoke({
            "input": query,
            "parsed": parsed_output,
            "context": context_text
        })

        message = final_output.get("answer", "").strip()
        return message

    except Exception as e:
        traceback.print_exc()
        return "Error processing query or file.", 500

if __name__ == "__main__":
    app.run(debug=True)

