from arango.client import ArangoClient

import config

# config variables
ARANGO_HOST = config.ARANGO_HOST
ARANGO_USERNAME = config.ARANGO_USERNAME
ARANGO_PASSWORD = config.ARANGO_PASSWORD

# initialize client
client = ArangoClient(hosts = config.ARANGO_HOST)

# connect to system
sys_db = client.db('_system', username = ARANGO_USERNAME, password = ARANGO_PASSWORD)

# connect to OpenContextData database
db = client.db("OpenContextData", username = ARANGO_USERNAME, password = ARANGO_PASSWORD)

# execute AQL query in datacommons_pairs
cursor = db.aql.execute("FOR doc IN datacommons_pairs RETURN doc")

# iterate through the cursor to retrieve the documents.
for document in cursor:
    print(document.get("raw").get("datePublished"))