import sys

content = open("main.py").read()
content = content.replace("import beliefs as belief_store", "import store as belief_store")
content = content.replace("def lifespan(app: FastAPI):", "def lifespan(app: FastAPI):\n    belief_store.init_db()")
content = content.replace("_beliefs = belief_store.load()", "_beliefs = belief_store.load()")
open("main.py", "w").write(content)
