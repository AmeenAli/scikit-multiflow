import os
import warnings
import re
import numpy as np
import pandas as pd
from timeit import default_timer as timer

from numpy import unique

from skmultiflow.evaluation.base_evaluator import StreamEvaluator
from skmultiflow.utils import constants


class EvaluatePrequentialDelayed(StreamEvaluator):
    """ The prequential evaluation method or interleaved test-then-train method.

    An alternative to the traditional holdout evaluation, inherited from
    batch setting problems.

    The prequential evaluation is designed specifically for stream settings,
    in the sense that each sample serves two purposes, and that samples are
    analysed sequentially, in order of arrival, and become immediately
    inaccessible.

    This method consists of using each sample to test the model, which means
    to make a predictions, and then the same sample is used to train the model
    (partial fit). This way the model is always tested on samples that it
    hasn't seen yet.

    Parameters
    ----------
    n_wait: int (Default: 200)
        The number of samples to process between each test. Also defines when to update the plot if `show_plot=True`.
        Note that setting `n_wait` too small can significantly slow the evaluation process.

    max_samples: int (Default: 100000)
        The maximum number of samples to process during the evaluation.

    batch_size: int (Default: 1)
        The number of samples to pass at a time to the model(s).

    pretrain_size: int (Default: 200)
        The number of samples to use to train the model before starting the evaluation. Used to enforce a 'warm' start.

    max_time: float (Default: float("inf"))
        The maximum duration of the simulation (in seconds).

    metrics: list, optional (Default: ['accuracy', 'kappa'])
        | The list of metrics to track during the evaluation. Also defines the metrics that will be displayed in plots
          and/or logged into the output file. Valid options are
        | **Classification**
        | 'accuracy'
        | 'kappa'
        | 'kappa_t'
        | 'kappa_m'
        | 'true_vs_predicted'
        | 'precision'
        | 'recall'
        | 'f1'
        | 'gmean'
        | **Multi-target Classification**
        | 'hamming_score'
        | 'hamming_loss'
        | 'exact_match'
        | 'j_index'
        | **Regression**
        | 'mean_square_error'
        | 'mean_absolute_error'
        | 'true_vs_predicted'
        | **Multi-target Regression**
        | 'average_mean_squared_error'
        | 'average_mean_absolute_error'
        | 'average_root_mean_square_error'
        | **Experimental** (no plot generated)
        | 'running_time'
        | 'model_size'

    output_file: string, optional (Default: None)
        File name to save the summary of the evaluation.

    show_plot: bool (Default: False)
        If True, a plot will show the progress of the evaluation. Warning: Plotting can slow down the evaluation
        process.

    restart_stream: bool, optional (default: True)
        If True, the stream is restarted once the evaluation is complete.

    data_points_for_classification: bool(Default: False)
        If True, the visualization used is a cloud of data points (only works for classification) and default
        performance metrics are ignored. If specific metrics are required, then they *must* be explicitly set
        using the ``metrics`` attribute.

    Notes
    -----
    1. This evaluator can process a single learner to track its performance; or multiple learners  at a time, to
       compare different models on the same stream.

    2. The metric 'true_vs_predicted' is intended to be informative only. It corresponds to evaluations at a specific
       moment which might not represent the actual learner performance across all instances.

    3. The metrics `running_time` and `model_size ` are not plotted when the `show_plot` option is set. Only their
       current value is displayed at the bottom of the figure. However, their values over the evaluation are written
       into the resulting csv file if the `output_file` option is set.

    Examples
    --------
    >>> # The first example demonstrates how to evaluate one model
    >>> from skmultiflow.data import SEAGenerator
    >>> from skmultiflow.trees import HoeffdingTreeClassifier
    >>> from skmultiflow.evaluation import EvaluatePrequential
    >>>
    >>> # Set the stream
    >>> stream = SEAGenerator(random_state=1)
    >>>
    >>> # Set the model
    >>> ht = HoeffdingTreeClassifier()
    >>>
    >>> # Set the evaluator
    >>>
    >>> evaluator = EvaluatePrequential(max_samples=10000,
    >>>                                 max_time=1000,
    >>>                                 show_plot=True,
    >>>                                 metrics=['accuracy', 'kappa'])
    >>>
    >>> # Run evaluation
    >>> evaluator.evaluate(stream=stream, model=ht, model_names=['HT'])

    >>> # The second example demonstrates how to compare two models
    >>> from skmultiflow.data import SEAGenerator
    >>> from skmultiflow.trees import HoeffdingTreeClassifier
    >>> from skmultiflow.bayes import NaiveBayes
    >>> from skmultiflow.evaluation import EvaluateHoldout
    >>>
    >>> # Set the stream
    >>> stream = SEAGenerator(random_state=1)
    >>>
    >>> # Set the models
    >>> ht = HoeffdingTreeClassifier()
    >>> nb = NaiveBayes()
    >>>
    >>> evaluator = EvaluatePrequential(max_samples=10000,
    >>>                                 max_time=1000,
    >>>                                 show_plot=True,
    >>>                                 metrics=['accuracy', 'kappa'])
    >>>
    >>> # Run evaluation
    >>> evaluator.evaluate(stream=stream, model=[ht, nb], model_names=['HT', 'NB'])

    >>> # The third example demonstrates how to evaluate one model
    >>> # and visualize the predictions using data points.
    >>> # Note: You can not in this case compare multiple models
    >>> from skmultiflow.data import SEAGenerator
    >>> from skmultiflow.trees import HoeffdingTreeClassifier
    >>> from skmultiflow.evaluation import EvaluatePrequential
    >>> # Set the stream
    >>> stream = SEAGenerator(random_state=1)
    >>> # Set the model
    >>> ht = HoeffdingTreeClassifier()
    >>> # Set the evaluator
    >>> evaluator = EvaluatePrequential(max_samples=200,
    >>>                                 n_wait=1,
    >>>                                 pretrain_size=1,
    >>>                                 max_time=1000,
    >>>                                 show_plot=True,
    >>>                                 metrics=['accuracy'],
    >>>                                 data_points_for_classification=True)
    >>>
    >>> # Run evaluation
    >>> evaluator.evaluate(stream=stream, model=ht, model_names=['HT'])

    """

    def __init__(self,
                 n_wait=200,
                 max_samples=100000,
                 batch_size=1,
                 pretrain_size=200,
                 max_time=float("inf"),
                 metrics=None,
                 output_file=None,
                 show_plot=False,
                 restart_stream=True,
                 data_points_for_classification=False):

        super().__init__()
        self._method = 'prequential'
        self._delayed_columns = ["X", "y_real", "y_pred", "arrival_time", "available_time"]
        self.n_wait = n_wait
        self.max_samples = max_samples
        self.pretrain_size = pretrain_size
        self.batch_size = batch_size
        self.max_time = max_time
        self.output_file = output_file
        self.show_plot = show_plot
        self.data_points_for_classification = data_points_for_classification

        if not self.data_points_for_classification:
            if metrics is None:
                self.metrics = [constants.ACCURACY, constants.KAPPA]

            else:
                if isinstance(metrics, list):
                    self.metrics = metrics
                else:
                    raise ValueError("Attribute 'metrics' must be 'None' or 'list', passed {}".format(type(metrics)))

        else:
            if metrics is None:
                self.metrics = [constants.DATA_POINTS]

            else:
                if isinstance(metrics, list):
                    self.metrics = metrics
                    self.metrics.append(constants.DATA_POINTS)
                else:
                    raise ValueError("Attribute 'metrics' must be 'None' or 'list', passed {}".format(type(metrics)))

        self.restart_stream = restart_stream
        self.n_sliding = n_wait

        warnings.filterwarnings("ignore", ".*invalid value encountered in true_divide.*")
        warnings.filterwarnings("ignore", ".*Passing 1d.*")

    def evaluate(self, stream, model, model_names=None):
        """ Evaluates a model or set of models on samples from a stream.

        Parameters
        ----------
        stream: Stream
            The stream from which to draw the samples.

        model: skmultiflow.core.BaseStreamModel or sklearn.base.BaseEstimator or list
            The model or list of models to evaluate.

        model_names: list, optional (Default=None)
            A list with the names of the models.

        Returns
        -------
        StreamModel or list
            The trained model(s).

        """
        self._init_evaluation(model=model, stream=stream, model_names=model_names)

        if self._check_configuration():
            self._reset_globals()
            # Initialize metrics and outputs (plots, log files, ...)
            self._init_metrics()
            self._init_plot()
            self._init_file()

            self.model = self._train_and_test

            if self.show_plot:
                self.visualizer.hold()

            return self.model

    def _sort_delay_queue(self):
        # sort values by available_time
        self.delay_queue = self.delay_queue.sort_values(by='available_time')
        # reset indexes
        self.delay_queue = self.delay_queue.reset_index(drop=True)

    def _get_delayed_samples(self):
        # get samples that have label available
        delayed_samples = self.delay_queue[self.delay_queue['available_time'] <= self.current_timestamp]
        # remove these samples from delay_queue
        self.delay_queue = self.delay_queue[self.delay_queue['available_time'] > self.current_timestamp]
        # transpose prediction matrix to model-sample again 
        y_pred = np.array(delayed_samples["y_pred"].to_list()).T.tolist()
        # return X, y_real and y_pred for the unqueued samples
        return (delayed_samples["X"].to_list(), delayed_samples["y_real"].to_list(), y_pred)

    def _update_classifiers(self, X, y):
        # check if there are samples to update
        if len(X) > 0:
            # Train
            if self.first_run:
                for i in range(self.n_models):
                    if self._task_type != constants.REGRESSION and \
                            self._task_type != constants.MULTI_TARGET_REGRESSION:
                        # Accounts for the moment of training beginning
                        self.running_time_measurements[i].compute_training_time_begin()
                        self.model[i].partial_fit(X, y, self.stream.target_values)
                        # Accounts the ending of training
                        self.running_time_measurements[i].compute_training_time_end()
                    else:
                        self.running_time_measurements[i].compute_training_time_begin()
                        self.model[i].partial_fit(X, y)
                        self.running_time_measurements[i].compute_training_time_end()

                    # Update total running time
                    self.running_time_measurements[i].update_time_measurements(self.batch_size)
                self.first_run = False
            else:
                for i in range(self.n_models):
                    self.running_time_measurements[i].compute_training_time_begin()
                    self.model[i].partial_fit(X, y)
                    self.running_time_measurements[i].compute_training_time_end()
                    self.running_time_measurements[i].update_time_measurements(self.batch_size)

    def _update_metrics_delayed(self, y_real_delayed, y_pred_delayed):
        # update metrics if y_pred_delayed has items
        if len(y_pred_delayed) > 0:
            for j in range(self.n_models):
                for i in range(len(y_pred_delayed[0])):
                    self.mean_eval_measurements[j].add_result(y_real_delayed[i], y_pred_delayed[j][i])
                    self.current_eval_measurements[j].add_result(y_real_delayed[i], y_pred_delayed[j][i])
            self._check_progress(self.actual_max_samples)
            if ((self.global_sample_count % self.n_wait) == 0 or
                    (self.global_sample_count >= self.max_samples) or
                    (self.global_sample_count / self.n_wait > self.update_count + 1)):
                if y_pred_delayed is not None:
                    self._update_metrics()
                self.update_count += 1

    def _predict_samples(self, X):
        if X is not None:
            # Test
            prediction = [[] for _ in range(self.n_models)]
            for i in range(self.n_models):
                try:
                    # Testing time
                    self.running_time_measurements[i].compute_testing_time_begin()
                    prediction[i].extend(self.model[i].predict(X))
                    self.running_time_measurements[i].compute_testing_time_end()
                except TypeError:
                    raise TypeError("Unexpected prediction value from {}"
                                    .format(type(self.model[i]).__name__))
            self.global_sample_count += self.batch_size
            # adapt prediction matrix to sample-model instead of model-sample by transposing it
            y_pred = np.array(prediction).T.tolist()
            # return predictions
            return y_pred

    def _update_delayed_queue(self, X, arrival_time, available_time, y_real, y_pred):
        delay_frame = pd.DataFrame(list(zip(X, y_real, y_pred, arrival_time, available_time)),
                                   columns=self._delayed_columns)
        # append new data to delayed queue
        self.delay_queue = self.delay_queue.append(delay_frame)
        # sort delay queue
        self._sort_delay_queue()

    @property
    def _train_and_test(self):
        """ Method to control the prequential evaluation.

        Returns
        -------
        BaseClassifier extension or list of BaseClassifier extensions
            The trained classifiers.

        Notes
        -----
        The classifier parameter should be an extension from the BaseClassifier. In
        the future, when BaseRegressor is created, it could be an extension from that
        class as well.

        """
        self._start_time = timer()
        self._end_time = timer()
        print('Prequential Evaluation Delayed')
        print('Evaluating {} target(s).'.format(self.stream.n_targets))

        self.actual_max_samples = self.stream.n_remaining_samples()
        if self.actual_max_samples == -1 or self.actual_max_samples > self.max_samples:
            self.actual_max_samples = self.max_samples

        self.first_run = True
        if self.pretrain_size > 0:
            print('Pre-training on {} sample(s).'.format(self.pretrain_size))

            # get current batch
            current_batch = self.stream.next_sample(self.pretrain_size)

            # TODO: improve this solution for more optional parameters than just weight
            # check if batch contains weight (change here if we include more informations in TemporalDataStream)
            if len(current_batch) > 4:
                X, arrival_time, available_time, y, weight = current_batch
            else:
                X, arrival_time, available_time, y = current_batch

            for i in range(self.n_models):
                if self._task_type == constants.CLASSIFICATION:
                    # Training time computation
                    self.running_time_measurements[i].compute_training_time_begin()
                    self.model[i].partial_fit(X=X, y=y, classes=self.stream.target_values)
                    self.running_time_measurements[i].compute_training_time_end()
                elif self._task_type == constants.MULTI_TARGET_CLASSIFICATION:
                    self.running_time_measurements[i].compute_training_time_begin()
                    self.model[i].partial_fit(X=X, y=y, classes=unique(self.stream.target_values))
                    self.running_time_measurements[i].compute_training_time_end()
                else:
                    self.running_time_measurements[i].compute_training_time_begin()
                    self.model[i].partial_fit(X=X, y=y)
                    self.running_time_measurements[i].compute_training_time_end()
                self.running_time_measurements[i].update_time_measurements(self.pretrain_size)
            self.global_sample_count += self.pretrain_size
            self.first_run = False

            # save actual timestamp, which is based on the last sample from the training data
            self.current_timestamp = arrival_time.to_list()[-1]
            # create dataframe to save delayed data
            # X = features
            # y_real = real label
            # y_pred = predicted label for each model being evaluated
            # arrival_time = arrival timestamp of the sample
            # available_time = timestamp when the sample label will be avilable
            self.delay_queue = pd.DataFrame(columns=self._delayed_columns)
            # transform time columns in datetime
            self.delay_queue['arrival_time'] = pd.to_datetime(self.delay_queue['arrival_time'])
            self.delay_queue['available_time'] = pd.to_datetime(self.delay_queue['available_time'])
            # sort delay queue
            self._sort_delay_queue()

        self.update_count = 0
        print('Evaluating...')
        while ((self.global_sample_count < self.actual_max_samples) & (
                self._end_time - self._start_time < self.max_time)
               & (self.stream.has_more_samples())):
            try:

                # get current batch
                current_batch = self.stream.next_sample(self.batch_size)

                # TODO: improve this solution for more optional parameters than just weight. Also, include weight in
                #  the delayed_queue check if batch contains weight (change here if we include more informations in
                #  TemporalDataStream)
                if len(current_batch) > 4:
                    X, arrival_time, available_time, y_real, weight = current_batch
                else:
                    X, arrival_time, available_time, y_real = current_batch

                # update current timestamp
                self.current_timestamp = arrival_time.to_list()[-1]

                # get delayed samples to update model before predicting a new batch
                X_delayed, y_real_delayed, y_pred_delayed = self._get_delayed_samples()

                self._update_metrics_delayed(y_real_delayed, y_pred_delayed)

                # before getting new samples, update classifiers with samples that are already available
                self._update_classifiers(X_delayed, y_real_delayed)

                # predict samples and get predictions
                y_pred = self._predict_samples(X)

                # add current samples to delayed queue
                self._update_delayed_queue(X, arrival_time, available_time, y_real, y_pred)

                self._end_time = timer()
            except BaseException as exc:
                print(exc)
                if exc is KeyboardInterrupt:
                    self._update_metrics()
                break

        # TODO: evaluate remaining samples in the delayed_queue
        # check if there are samples in delay_queue
        if self.delay_queue.shape[0] > 0:
            # sort remaining samples again
            self._sort_delay_queue()
            # iterate over delay_queue while it has samples according to batch_size
            while (self.delay_queue.shape[0] > 0) & (self.delay_queue.shape[0] - self.batch_size > 0):
                # current samples to process
                samples = self.delay_queue[:self.batch_size]
                # TODO: process samples
                # drop samples and update delay_queue
                self.delay_queue = self.delay_queue.drop(self.delay_queue.index[[np.arange(self.batch_size)]])
            # check if we still have samples in queue (delay_queue size < batch_size)
            if self.delay_queue.shape[0] > 0:
                # TODO: process remaining samples
                pass

        # Flush file buffer, in case it contains data
        self._flush_file_buffer()

        if len(set(self.metrics).difference({constants.DATA_POINTS})) > 0:
            self.evaluation_summary()
        else:
            print('Done')

        if self.restart_stream:
            self.stream.restart()

        return self.model

    def partial_fit(self, X, y, classes=None, sample_weight=None):
        """ Partially fit all the models on the given data.

        Parameters
        ----------
        X: Numpy.ndarray of shape (n_samples, n_features)
            The data upon which the algorithm will create its model.

        y: Array-like
            An array-like containing the classification labels / target values for all samples in X.

        classes: list
            Stores all the classes that may be encountered during the classification task. Not used for regressors.

        sample_weight: Array-like
            Samples weight. If not provided, uniform weights are assumed.

        Returns
        -------
        EvaluatePrequential
            self

        """
        if self.model is not None:
            for i in range(self.n_models):
                if self._task_type == constants.CLASSIFICATION or \
                        self._task_type == constants.MULTI_TARGET_CLASSIFICATION:
                    self.model[i].partial_fit(X=X, y=y, classes=classes, sample_weight=sample_weight)
                else:
                    self.model[i].partial_fit(X=X, y=y, sample_weight=sample_weight)
            return self
        else:
            return self

    def predict(self, X):
        """ Predicts with the estimator(s) being evaluated.

        Parameters
        ----------
        X: Numpy.ndarray of shape (n_samples, n_features)
            All the samples we want to predict the label for.

        Returns
        -------
        list of numpy.ndarray
            Model(s) predictions

        """
        predictions = None
        if self.model is not None:
            predictions = []
            for i in range(self.n_models):
                predictions.append(self.model[i].predict(X))

        return predictions

    def get_info(self):
        info = self.__repr__()
        if self.output_file is not None:
            _, filename = os.path.split(self.output_file)
            info = re.sub(r"output_file=(.\S+),", "output_file='{}',".format(filename), info)

        return info