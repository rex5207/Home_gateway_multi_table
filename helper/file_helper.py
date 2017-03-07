import cPickle as pickle
import logging


def save(filename, dict):
    try:
        with open(filename, 'wb') as fp:
            pickle.dump(dict, fp)
        return True
    except:
        logging.warning('Failed when saving pickled')
        return False


def load(filename):
    try:
        with open(filename, 'rb') as fp:
            return pickle.load(fp)
    except:
        logging.warning('Failed when loading pickled')
        return None
