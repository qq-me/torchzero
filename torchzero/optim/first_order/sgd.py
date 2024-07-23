import torch
from torch import optim
from ..utils import get_group_params_and_grads, get_group_params_and_grads_tensorlist
from ...random.random import randmask
from .. import _foreach
__all__ = [
    #"GD",
    "SignGD",
    "BitGD",
    "SoftSignGD",
]
#region GD
class GD(optim.Optimizer):
    def __init__(self, params, lr, foreach=True):
        """Gradient descent.

        Args:
            params (_type_): _description_
            lr (_type_): _description_
            foreach (bool, optional): _description_. Defaults to True.
        """
        super().__init__(params, dict(lr=lr))
        self.foreach = foreach

    @torch.no_grad
    def step(self, closure=None): # type:ignore
        loss = None
        if closure is not None:
            with torch.enable_grad(): loss = closure()

        for group in self.param_groups:
            params, grads = get_group_params_and_grads(group, with_grad=True)
            _foreach.sub_(params, grads, alpha = group['lr'], foreach = self.foreach)

        return loss
#endregion
#region SignGD
class SignGD(optim.Optimizer):
    def __init__(self, params, lr, foreach=True):
        """Sign gradient descent. Uses sign of the gradient to update the parameters.

        Args:
            params (_type_): _description_
            lr (_type_): _description_
            foreach (bool, optional): _description_. Defaults to True.
        """
        super().__init__(params, dict(lr=lr))
        self.foreach = foreach

    @torch.no_grad
    def step(self, closure=None): # type:ignore
        loss = None
        if closure is not None:
            with torch.enable_grad(): loss = closure()

        for group in self.param_groups:
            params, grads = get_group_params_and_grads_tensorlist(group, with_grad=True, foreach=self.foreach)
            params.sub_(grads.sign(), alpha = group['lr'])

        return loss
#endregion
#region BitGD
class BitGD(optim.Optimizer):
    def __init__(self, params, lr, foreach = True):
        """Operates on parameters that can have ether 1 or -1 as the value.

        Args:
            params (_type_): _description_
            lr (_type_): Probability that a parameter will be updated by the gradient.
        """
        super().__init__(params, dict(lr=lr))

        self.foreach = foreach

    @torch.no_grad
    def step(self, closure=None): # type:ignore
        loss = None
        if closure is not None:
            with torch.enable_grad(): loss = closure()

        for group in self.param_groups:
            params, grads = get_group_params_and_grads_tensorlist(group, with_grad=True, foreach=self.foreach)
            # assign new weights to params.data
            params.set_(
                # generate a random mask with `lr` probability for each value to be True;
                # where mask is True, set parameters to `- gradient.sign()`.
                [p.where(randmask(grad.size(), p = group['lr'], device=grad.device), grad) for p,grad in zip(
                    params,
                    # negate the sign of the gradient
                    grads.sign().neg()
                )]
            )
        return loss
#endregion

#region SoftSignGD
class SoftSignGD(optim.Optimizer):
    def __init__(self, params, lr, foreach = True):
        """Softsign gradient descent. Halfway between normal gradient descent and sign gradient descent.
        Uses softsign of the gradient to update the parameters,
        which normalizes the amplitudes without completely discarding them like in sign gradient descent.

        Args:
            params (_type_): _description_
            lr (_type_): _description_
            foreach (bool, optional): _description_. Defaults to True.
        """
        super().__init__(params, dict(lr=lr))
        self.foreach = foreach

    @torch.no_grad
    def step(self, closure=None): # type:ignore
        loss = None
        if closure is not None:
            with torch.enable_grad(): loss = closure()

        for group in self.param_groups:
            params, grads = get_group_params_and_grads_tensorlist(group, with_grad=True, foreach=self.foreach)
            params.sub_(grads.softsign(), alpha=group['lr'])
        return loss
#endregion

