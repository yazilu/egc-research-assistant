"""
Pure Python shim for datrie.Trie to avoid C compilation on Windows.
Compatible with the subset of datrie API used by rag_tokenizer.py.
"""
import pickle


class Trie:
    def __init__(self, alphabet):
        self._alphabet = alphabet
        self._data = {}

    @staticmethod
    def load(path):
        with open(path, "rb") as f:
            data = pickle.load(f)
        obj = Trie(data["alphabet"])
        obj._data = data["data"]
        return obj

    def save(self, path):
        with open(path, "wb") as f:
            pickle.dump({"alphabet": self._alphabet, "data": self._data}, f)

    def has_keys_with_prefix(self, prefix):
        prefix = prefix.lower()
        for key in self._data:
            if key.startswith(prefix):
                return True
        return False

    def __getitem__(self, key):
        return self._data[key.lower()]

    def __setitem__(self, key, value):
        self._data[key.lower()] = value

    def __contains__(self, key):
        return key.lower() in self._data

    def keys(self):
        return self._data.keys()
