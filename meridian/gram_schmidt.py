import numpy as np


def gram_schmidt(latency_matrix):
    x = latency_matrix.to_numpy()
    Q, R = np.linalg.qr(x)
    return Q
