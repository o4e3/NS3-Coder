# Step 1. Knowledge Base 구축
import os
import warnings
from langchain_community.document_loaders import PyMuPDFLoader
from PyPDF2 import PdfMerger
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_community.llms import HuggingFacePipeline

warnings.filterwarnings("ignore")

# 여러 PDF를 하나로 합치기 (./ns3coder/ns3.40_docs)
output = '/home/gpuadmin/ns3coder/psh/data_cleaning/O/model-library_clean_complete.pdf'

if os.path.exists('/home/gpuadmin/ns3coder/psh/data_cleaning/O/rlibDB') :
    print('A RAG DB already exists. Exist DB will be loaded.')
    # 임베딩 모델 초기화 (VectorDB 생성 시 사용한 설정과 동일하게)
    embeddings = HuggingFaceEmbeddings(
        model_name='BAAI/bge-m3',
        model_kwargs={'device':'cuda'},
        encode_kwargs={'normalize_embeddings': True},
    )

    # 저장된 Chroma VectorDB 경로 설정
    vectorstore_path = '/home/gpuadmin/ns3coder/psh/data_cleaning/O/rlibDB'

    # 저장된 VectorDB 불러오기
    vectorstore = Chroma(persist_directory=vectorstore_path, embedding_function=embeddings)
else : 
    if os.path.exists(output):
        print('A merged PDF already exists.')
    else:
        pdf_folder = '/home/gpuadmin/ns3coder/psh/data_cleaning/O'  # PDF들이 들어 있는 폴더 경로
        pdf_files = [os.path.join(pdf_folder, file) for file in os.listdir(pdf_folder) if file.endswith('.pdf')]

        merger = PdfMerger()

        for pdf in pdf_files:
            merger.append(pdf)

        merger.write(output)
        merger.close()
        print('PDF was merged.')

    #NS 3.40 Docs pdf를 PyMuPDFLoader를 이용해 로드
    loader = PyMuPDFLoader(output)
    pages = loader.load()

    #Docs를 문장으로 분리 (Chunk size : 500, 각 청크의 50자씩은 겹치게 나눌 것임(overlap))
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    docs = text_splitter.split_documents(pages)

    # Embedding
    embeddings = HuggingFaceEmbeddings(
        model_name='BAAI/bge-m3',
        model_kwargs={'device':'cuda'},
        encode_kwargs={'normalize_embeddings':True},
    )

    # Chroma Vector DB 구축
    vectorstore = Chroma.from_documents(docs, embeddings)
    ## 경로 설정
    vectorstore_path = '/home/gpuadmin/ns3coder/psh/data_cleaning/O/rlibDB'
    os.makedirs(vectorstore_path, exist_ok=True)
    ### Vector DB 생성 및 저장
    vectorstore = Chroma.from_documents(docs, embeddings, persist_directory=vectorstore_path)
    vectorstore.persist()
    print("Vector DB created and saved.")

# Step 2. Retriever 정의
retriever = vectorstore.as_retriever(search_kwargs={'k':3})

# Step 3. LangChain & Generate
from transformers import AutoTokenizer, AutoModelForCausalLM, TextStreamer, BitsAndBytesConfig
import torch
import transformers

torch.cuda.empty_cache()

quantization_config = BitsAndBytesConfig(
    load_in_8bit = True
)

model_id = "meta-llama/Llama-3.3-70B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=quantization_config,
    device_map="auto"
)
print(f"{model_id} loaded sucessfully.")
pipe = transformers.pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=5000,  
    do_sample=True,
    temperature=0.7
)

# LangChain에서 사용할 LLM 인터페이스로 변환
llm = HuggingFacePipeline(pipeline=pipe)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",  # "stuff" 방식은 검색된 문서 전체를 하나의 prompt에 넣어 처리
    retriever=retriever
)

# 예시 질의
input_text = "What is the purpose of the NetAnim tool in the NS-3 model library, and how is it typically used in simulations?"
input_prompt = f"Let's think step by step. You're NS3 coder. {input_text}"
answer = qa_chain.run(input_prompt)

print("Answer:", answer)