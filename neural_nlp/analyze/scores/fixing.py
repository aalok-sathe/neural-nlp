import logging
import numpy as np
import pickle
import sys
from pathlib import Path
from scipy.stats import median_absolute_deviation
from tqdm import tqdm

from brainscore.metrics.transformations import standard_error_of_the_mean


def testing():
    with open('/braintree/home/msch/.result_caching/neural_nlp.score/'
              'benchmark=Pereira2018-encoding,model=gpt2-xl,subsample=None.pkl', 'rb') as f:
        ceiled_score = pickle.load(f)['data']
        best_layer = ceiled_score.sel(aggregation='center').argmax('layer')
        ceiled_score = ceiled_score.isel(layer=best_layer.values)
    # overview
    ceiled_center, ceiled_error = ceiled_score.sel(aggregation='center'), ceiled_score.sel(aggregation='error')
    print(f"ceiled: {ceiled_center.values:.2f}-+{ceiled_error.values:.2f}")
    unceiled_score = ceiled_score.raw
    unceiled_center, unceiled_error = unceiled_score.sel(aggregation='center'), unceiled_score.sel(aggregation='error')
    print(f"unceiled: {unceiled_center.values:.2f}-+{unceiled_error.values:.2f}")
    ceiling_score = ceiled_score.ceiling
    ceiling_center = ceiling_score.sel(aggregation='center').values
    print(f"ceiling: {ceiling_center:.2f}-+["
          f"{ceiling_score.sel(aggregation='error_low').values:.2f},"
          f"{ceiling_score.sel(aggregation='error_high').values:.2f}]")
    # reproduce
    raw = unceiled_score.raw
    subject_scores = raw.groupby('subject').median('neuroid')
    repr_center, repr_error = subject_scores.median(), standard_error_of_the_mean(subject_scores, dim='subject')
    repr_center, repr_error = repr_center / ceiling_center, repr_error / ceiling_center
    print(f"reproduce: {repr_center.values:.2f}-+{repr_error.values:.2f}")
    # MAD
    mad_error = median_absolute_deviation(subject_scores.values)
    mad_error /= ceiling_center
    print(f"MAD: {repr_center.values:.2f}-+{mad_error:.2f}")


def change():
    dir = Path('/braintree/home/msch/.result_caching/neural_nlp.score/')
    pereira_scores = list((dir.glob('benchmark=Pereira2018-encoding,model=*.pkl')))
    print(f"fixing {len(pereira_scores)} Pereira scores")
    iterator = tqdm(pereira_scores, desc='Pereira scores')
    for score_file in iterator:
        iterator.set_postfix_str(score_file.name)
        with open(score_file, 'rb') as f:
            ceiled_score = pickle.load(f)['data']
        unceiled_score = ceiled_score.raw
        # recompute
        raw = unceiled_score.raw
        subject_scores = raw.groupby('subject').median('neuroid')
        subject_values = np.nan_to_num(subject_scores.values, nan=0)
        unceiled_error = median_absolute_deviation(subject_values, axis=subject_scores.dims.index('subject'))
        ceiled_error = unceiled_error / ceiled_score.ceiling.sel(aggregation='center').values
        # set
        ceiled_score.loc[{'aggregation': 'error'}] = ceiled_error  # will apply to unceiled score due to apply_raw
        unceiled_score.loc[{'aggregation': 'error'}] = unceiled_error
        # update file
        with open(score_file, 'wb') as f:
            pickle.dump({'data': ceiled_score}, f, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    change()
