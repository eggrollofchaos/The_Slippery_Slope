"""Evaluation environments for The Slippery Slope.

- ShellGameEnv: 3-cups-1-ball deception testbed. Dealer is rewarded for
  misleading the user about the true ball position.
- PyTransferEnv: minimal novel-transfer probe. Does reward-gaming learned
  in the shell game generalize to a coding task where the "secret score"
  lives in a file the model can see?
"""

from .shell_game import ShellGameEnv
from .py_transfer import PyTransferEnv

__all__ = ["ShellGameEnv", "PyTransferEnv"]
