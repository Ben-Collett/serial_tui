def merge_dicts(dict1: dict, dict2: dict):
    for k, v in dict2.items():
        if k not in dict1:
            dict1[k] = v
        elif k in dict1 and isinstance(v, dict) and isinstance(dict1[k], dict):
            merge_dicts(dict1[k], v)
