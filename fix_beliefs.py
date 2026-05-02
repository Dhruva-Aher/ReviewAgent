import beliefs as belief_store
def read():
    d = belief_store.load()
    if 'repos' not in d:
        d['repos'] = {}
        belief_store.save(d)

read()
