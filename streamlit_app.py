#
#
#

#from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.functions import sum, col
from snowflake.snowpark import Session
import altair as alt
import streamlit as st
import logging
import requests
import os

# Set page config
st.set_page_config(layout="wide")

# Get current session
# session = get_active_session()

connection_parameters = {
   "account": os.getenv("SF_ACCOUNT_IDENTIFIER"),
   "user": os.getenv("SF_USER"),
   "password": os.getenv("SF_PASSWORD"),
   "role": os.getenv("SF_ROLE"),  # optional
   "warehouse": os.getenv("SF_WAREHOUSE"),  # optional
   # "database": os.getenv(),  # optional
 }

session = Session.builder.configs(connection_parameters).create()

config = {
    "production": {
        "descriptions": "BRAIN.RAW_MYSQL_BRAIN_USER.BRUS_REL_OBJECTS",
    },
    "staging": {
        "descriptions": "BRAIN_STAGING.RAW_STG_MYSQL_BRUS_BRAIN_USER_DEVELOPMENT.BRUS_REL_OBJECTS",
    }
}


@st.cache_data()
def load_data(env, user_id, uuids=None):
    # Load CO2 emissions data
    descriptions = (
        session
        .table(env["descriptions"])
        .filter(col('description') != '')
        .filter(col('name') == 'studio_project')
        .filter(col('user_id') == user_id)
        .sort(col('created_at').desc())
        .select([col(each) for each in ('name', 'user_id', 'description', 'created_at')])
    )
    if uuids:
        descriptions.filter(col('uuid').in_(uuids))

    return descriptions.count(), descriptions.to_pandas()


ObjectDb = None
RealtionDb = None


class VectorStore:

    metadata = None

    @classmethod
    def delete_index(cls):
        metadata = cls.metadata

        r = requests.delete(
            f"{RETRIEVAL}/delete",
            json={
                "filter": {
                    "source": metadata['source'],
                    "author": metadata['author']
                }
            },
            headers={"Authorization": f"token {os.getenv('BRUS_TOKEN')}", "Content-Type": "application/json"}
        )
        return r

    @classmethod
    def query(cls, query, top_k=1):
        metadata = VectorStore.metadata
        queries = {
            "queries": [{
                "query": query,
                "filter": {
                    # "document_id": "string",
                    # "source": "email",
                    "source": metadata['source'],  # ObjectDb.Type.Studio.Project.value,
                    # "source_id": "string",
                    "author": metadata['author'],
                },
                "top_k": top_k
            }]
        }
        r = requests.post(
            f"{RETRIEVAL}/query",
            json=queries,
            headers={"Authorization": f"token {os.getenv('BRUS_TOKEN')}", "Content-Type": "application/json"}
        )
        print(r.json())
        logging.warning(r.json())
        # document_id is same as id/uuid during upsert
        uuids = [each.get('metadata').get('document_id') for each in r.json().get('results', [])[0]['results']]
        scores = {each.get('metadata').get('document_id'): each.get('score') for each in r.json().get('results', [])[0]['results']}
        return uuids, scores

# Load and cache data
environment = "staging"
user_id = 246

BRUS = os.getenv('BRUS') or "https://api-dev.braininc.net"
RETRIEVAL = os.getenv('RETRIEVAL') or "https://api-dev.braininc.net/be/retrieval"
PINECONE_ENV = environment
metadata = {
    "source": "chat",  # ObjectDb.Type.Studio.Project.value,
    # "source_id": null,
    # "url": null,
    # "created_at": null,
    "author": f"{PINECONE_ENV}/{user_id}",
    # no need to pass document_id as it same as id during upsert
    # https://github.com/openai/chatgpt-retrieval-plugin/blob/main/services/chunks.py#LL119C1-L119C1
    # "document_id": "a600078a-0cb2-457d-806c-8ae701790b59"
}
VectorStore.metadata = metadata

query = st.text_input('Similarity Search', 'plan my trip to europe')
if query:
    uuids, scores = VectorStore.query(query)
    count, descriptions = load_data(config[environment], user_id, uuids)
    st.text(f"number of projects {count}")
    st.table(descriptions)
else:
    count, descriptions = load_data(config[environment], user_id)
    st.text(f"number of projects {count}")
    st.table(descriptions)
