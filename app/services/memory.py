_memory_store = []


def load_memory():
    return list(_memory_store)


def save_memory(entry):
    _memory_store.append(entry)
    if len(_memory_store) > 8:
        _memory_store.pop(0)


def memory_context():
    if not _memory_store:
        return "No prior campaign history."

    return "\n".join([
        f"- Product: {m['product']} | Tone: {m['tone']}"
        for m in _memory_store
    ])