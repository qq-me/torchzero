# torchzero
There aren't many gradient free optimizers for pytorch, so I made a few algorithms into pytorch optimizers. Though this library is not limited to just gradient free ones. Note: Largely WIP

## 0th order optimization using Random Gradients
Quick derivative-free recipe for 68% accuracy on MNIST in 10 epochs with a 15k parameters convolutional neural network (can probably get better with tuning):
```py
from torchzero.optim import RandomGrad
optimizer = RandomGrad(model.parameters(), magn=1e-5, opt=optim.AdamW(model.parameters(), lr=1e-3))

torch.set_grad_enabled(False)
for epoch in range(10):
    for inputs, targets in dataloader: # I used batch size of 32
        @torch.no_grad()
        def closure():
            optimizer.zero_grad()
            preds = model(inputs)
            loss = loss_fn(preds, targets)
            # loss.backward() - not needed
            return loss
        loss = optimizer.step(closure)
```

So what is happening there? We generate a random petrubation to model parameters and reevaluate the loss, if it increases, set `grad` to petrubation, otherwise `grad` to minus petrubation. And then your favourite optimizer uses its update rules!

We can go further, an evolving swarm of 10 of those reaches 82% test accuracy in 10 epochs, evaluating the model 10 times per step. I did 0 tuning so it can probably get better, and the accuracy was steadily increasing at the end so more epochs would help.
```py
from torchzero.optim import RandomGrad, SwarmOfOptimizers
optimizers = [
    RandomGrad(model.parameters(), magn=1e-5, opt=optim.AdamW(model.parameters(), 1e-3))
    for _ in range(10)
]
# a swarm is also an torch.optim.Optimizer and uses the same API
swarm = SwarmOfOptimizers(model.parameters(), optimizers, old_steps=5, die_after=20, crossover_p=0.9) 
```
Each optimizer in a swarm optimizes its own copy of model parameters, and, whenever some optimizer performs badly, it dies and respawns with new parameters that are a crossover between two best optimizers. This can also work on gradient-descent optimizers, but it (currently) won't work well with most optimizers other than plain SGD because momentum doesn't know about all those new swarm update rules.

All MNIST experiments are in [this notebook](https://nbviewer.org/github/qq-me/torchzero/blob/main/notebooks/datasets/mnist%20randomgrad.ipynb), and a quick comparison of all hyperparameters I tested in [this notebook](https://nbviewer.org/github/qq-me/torchzero/blob/main/notebooks/datasets/mnist%20summary.ipynb).

## Gradient chaining
Gradient chaining means that after one optimizer updates parameters of the model, the update is undone and used as gradients for the next optimizer. There are two uses - firstly, this lets you combine multiple optimizers, specifically for adding types of momentum to optimizers that don't implement them, secondly, you can use derivative-free optimizers to generate gradients for any gradient-based optimizer, like RandomGrad does.  
Here is how you can add Nesterov momentum to any optimizer:
```py
from collie.optim.lion import Lion
from torchzero.optim import GradChain

# Since SGD simply subtracts the gradient, by chaining optimizers with SGD, we can essentially add pure Nesterov momentum
# we can apply Nesterov momentum before Lion optimizer update rules kick in:
optimizer = GradChain(
    model.parameters(),
    [
        torch.optim.SGD(model.parameters(), lr=1 momentum=0.9, nesterov=True),
        Lion(model.parameters(), lr=1e-2),
    ],
)
# or after, by swapping them
optimizer = GradChain(
    model.parameters(),
    [
        Lion(model.parameters(), lr=1e-2),
        torch.optim.SGD(model.parameters(), lr=1, momentum=0.9, nesterov=True),
    ],
)
```

## Derivative-free optimization methods
The `optim` submodule implements some derivative-free optimization methods in a form of pytorch optimizers that fully support the pytorch optimizer API, including random search, shrinking random search, grid search, sequential search, random walk, second order random walk. There is also swarm of optimizer which supports both gradient based and gradient free optimizers. I don't really want to do docs yet but they should be straightforward to use. I haven't tested their performance much but that is the goal. You can also check the [notebooks](https://github.com/qq-me/torchzero/tree/main/notebooks/algos) for some visualizations.

Available standalone optimizers:
- GridSearch - tries all possible combinations of parameters
- SequentialSearch - iteratively tries all possible values of each parameter sequentially
- RandomSearch - tries random parameters
- RandomWalk - 1st order random walk generates random petrubation to parameters and saves it if loss decreases. Higher order random walks generate petrubations to higher order directions
- SPSA - simultaneous perturbation stochastic approximation, also uses random petrubations but in a different way from random walk.
- Stochastic Three Points from https://arxiv.org/pdf/1902.03591
- Two-step random search from https://arxiv.org/pdf/2110.13265

Gradient approximators, that approximate gradients for gradient based optimizers:
- RandomGrad - generate a random petrubation to model parameters and reevaluate the loss, if it increases, set gradient to petrubation, otherwise set gradient to minus petrubation
- SPSA - can also work as gradient approximator, so you get AdamSPSA or your-favourite-opimizer-SPSA for free.

Optimizer wrappers:
- UpdateToGrad - converts optimizer update into a gradient, so you can use any gradient-free optimizer as gradient approximator, or combine gradient-based optimizers
- GradientChain - chains optimizers using UpdateToGrad
- SwarmOfOptimizers - a swarm of optimizers, can function as a genetic algorithm or as a particle optimization algorithm depending on parameters
- OptimizerAverage - averages the updates of given optimizers.
- FractionalOptimizer - wraps any gradient-based optimizer and gives it fractional order as described in https://www.mdpi.com/2504-3110/7/7/500
