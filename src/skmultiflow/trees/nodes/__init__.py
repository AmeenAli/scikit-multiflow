"""
The :mod:`skmultiflow.trees.nodes` module includes learning and split node
implementations for the hoeffding trees.
"""

from .core import FoundNode, Node, SplitNode, LearningNodeMixin, ActiveLeafMixin, \
    InactiveLeafMixin, AdaNode
from .htc_nodes import ActiveLearningNodeMC, InactiveLearningNodeMC, ActiveLearningNodeNB, \
    ActiveLearningNodeNBA
from .hatc_nodes import AdaSplitNode, AdaLearningNode  # TODO: verify name
from .arf_htc_nodes import RandomActiveLearningNodeMC, RandomActiveLearningNodeNB, \
    RandomActiveLearningNodeNBA
from .efdtc_nodes import EFDTSplitNode, EFDTActiveLearningNodeMC, EFDTInactiveLearningNodeMC, \
    EFDTActiveLearningNodeNB, EFDTActiveLearningNodeNBA
from .lc_htc_nodes import LCActiveLearningNodeMC, LCInactiveLearningNodeMC, \
    LCActiveLearningNodeNB, LCActiveLearningNodeNBA

# TODO continue from here
from .htr_nodes import ActiveLearningNodeForRegression, ActiveLearningNodePerceptron, \
    InactiveLearningNodeForRegression, InactiveLearningNodePerceptron
from .arf_htr_nodes import RandomLearningNodeForRegression, RandomLearningNodePerceptron
from .hatr_nodes import AdaSplitNodeForRegression, AdaLearningNodeForRegression
from .isouptr_nodes import ActiveLearningNodePerceptronMultiTarget, \
    ActiveLearningNodeAdaptiveMultiTarget, InactiveLearningNodePerceptronMultiTarget, \
    InactiveLearningNodeAdaptiveMultiTarget
from .sst_htr_nodes import SSTActiveLearningNode, SSTActiveLearningNodeAdaptive, \
    SSTInactiveLearningNode, SSTInactiveLearningNodeAdaptive


__all__ = ["FoundNode", "Node", "LearningNodeMixin", "ActiveLeafMixin", "InactiveLeafMixin",
           "SplitNode", "ActiveLearningNodeMC", "InactiveLearningNodeMC",
           "ActiveLearningNodeNB", "ActiveLearningNodeNBA",
           "RandomActiveLearningNodeMC", "RandomActiveLearningNodeNB",
           "RandomActiveLearningNodeNBA", "AdaNode", "AdaSplitNode", "AdaLearningNode",
           "EFDTSplitNode", "EFDTActiveLearningNodeMC", "EFDTInactiveLearningNodeMC",
           "EFDTActiveLearningNodeNB", "EFDTActiveLearningNodeNBA",
           "LCActiveLearningNodeMC", "LCInactiveLearningNodeMC", "LCActiveLearningNodeNB",
           "LCActiveLearningNodeNBA", "ActiveLearningNodeForRegression",
           "ActiveLearningNodePerceptron", "InactiveLearningNodeForRegression",
           "InactiveLearningNodePerceptron", "RandomLearningNodeForRegression",
           "RandomLearningNodePerceptron", "AdaSplitNodeForRegression",
           "AdaLearningNodeForRegression", "ActiveLearningNodeForRegressionMultiTarget",
           "ActiveLearningNodePerceptronMultiTarget", "ActiveLearningNodeAdaptiveMultiTarget",
           "InactiveLearningNodePerceptronMultiTarget", "InactiveLearningNodeAdaptiveMultiTarget",
           "SSTActiveLearningNode", "SSTActiveLearningNodeAdaptive", "SSTInactiveLearningNode",
           "SSTInactiveLearningNodeAdaptive"]
