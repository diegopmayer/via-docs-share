import streamlit as st
import awswrangler as wr
import boto3
import tempfile
import zipfile
import os
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import shutil

with open('src/config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

aws_access_key_id = st.secrets["awscredentials"]["aws_access_key_id"]
aws_secret_access_key = st.secrets["awscredentials"]["aws_secret_access_key"]
region_name = st.secrets["awscredentials"]["region"]

boto3_session = boto3.Session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=region_name
)

def login_user():

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
    authenticator.login()

    if st.session_state['authentication_status']:

        main()
    elif st.session_state['authentication_status'] is False:
        st.error("Usuário/Senha inválido")
    elif st.session_state["authentication_status"] is None:
        st.warning("Por favor, utilize seu usuário senha!")

def list_subfolders(bucket_name, object_name, purpose):
    """Função para listar subpastas/arquivos dentro de um prefixo específico no bucket S3."""
    prefix = f's3://{bucket_name}/{object_name}/{purpose}/'
    objects = wr.s3.list_objects(path=prefix, boto3_session=boto3_session)
    return objects

def generate_presigned_url(bucket_name, key, expiration=3600):
    """Gera um URL pré-assinado para download do S3."""
    s3_client = boto3_session.client('s3')
    response = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': key},
        ExpiresIn=expiration
    )
    return response

def download_all_files(bucket_name, object_paths):
    """Cria um arquivo zip com todos os arquivos especificados e retorna o caminho local."""
    tmpdirname = tempfile.mkdtemp()  # Cria um diretório temporário, que não será automaticamente deletado
    zip_filename = os.path.join(tmpdirname, 'download.zip')
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for s3_path in object_paths:
            key = '/'.join(s3_path.split('/')[3:])  # Extrai a chave do caminho completo
            local_filename = os.path.join(tmpdirname, os.path.basename(key))
            wr.s3.download(path=s3_path, local_file=local_filename, boto3_session=boto3_session)
            zipf.write(local_filename, os.path.basename(local_filename))
    return zip_filename, tmpdirname


def main():
    st.title("Arquivos da BP Viavante")
    
    purpose = st.text_input("Digite o número da proposta:", "")
    bucket_name = 'unus-solutions' 
    object_name = 'viavante_docs'

    if purpose:
        subfolders = list_subfolders(bucket_name, object_name, purpose)

        if subfolders:
            st.write(f"Subpastas/arquivos encontrados em '{purpose}':")
            object_paths = []
            for subfolder in subfolders:
                # Criar o link de download
                key = '/'.join(subfolder.split('/')[3:])  # Extrair a chave relativa
                key_legend = '/'.join(subfolder.split('/')[5:]) # legenda para aparecer na página
                download_link = generate_presigned_url(bucket_name, key)
                st.markdown(f"[{key_legend}]({download_link})", unsafe_allow_html=True)
                # object_paths.append(subfolder)
            
            # Botão para baixar todos os arquivos
            if st.button("Baixar todos os arquivos"):
                zip_path, tmpdirname = download_all_files(bucket_name, subfolders)
                with open(zip_path, "rb") as f:
                    st.download_button(
                        label="Clique aqui para baixar todos os arquivos",
                        data=f,
                        file_name=f"{purpose}.zip",
                        mime="application/zip"
                    )
                    # Após o uso do arquivo zip, você pode limpar o diretório manualmente:
                    shutil.rmtree(tmpdirname)
        else:
            st.write(f"A proposta {purpose} NÃO existe!")

def logout_user():
    """Função para efetuar logout limpando a sessão do Streamlit."""
    if 'authentication_status' in st.session_state:
        del st.session_state['authentication_status']
    st.experimental_rerun()  # Reinicia o script para forçar um logout

# Registrar a função de logout quando a página for fechada
st.session_state.on_session_shutdown = logout_user

if __name__ == "__main__":
        # Limpar o estado da autenticação toda vez que a página for recarregada ou nova execução
    if 'authentication_status' in st.session_state:
        st.session_state['logout'] = True
        # st.session_state.clear()
        login_user()
    else:
        login_user()
