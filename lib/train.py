import torch
import numpy as np
from torch.autograd import Variable
from const import *
import time
import torch.nn.functional as F


class AlphaLoss(torch.nn.Module):
    def __init__(self):
        super(AlphaLoss, self).__init__()

    def forward(self, winner, self_play_winner, probas, self_play_probas):
        value_error = F.mse_loss(winner, self_play_winner)
        if NO_MCTS:
            policy_error = F.binary_cross_entropy(probas, self_play_probas)
        else:
            policy_error = F.cross_entropy(probas, self_play_probas)
        return value_error + policy_error



def train_epoch(player, optimizer, example, criterion):
    """ Used to train the 3 models over a single batch """

    optimizer.zero_grad()

    feature_maps = player.extractor(example['state'])
    winner = player.value_net(feature_maps)
    probas = player.policy_net(feature_maps)

    loss = criterion(winner.view(-1), example['winner'], probas, example['move'])
    loss.backward()
    optimizer.step()

    return loss



def train(dataloader, player, epoch):
    """ Train the models using the data generated by the self-play """

    ## Add the weights of the feature extractor to both the 
    ## policy and the value so they get both optimized by the loss
    joint_params = list(player.extractor.parameters()) + \
                   list(player.policy_net.parameters()) +\
                   list(player.value_net.parameters())

    optimizer = torch.optim.SGD(joint_params, lr=LR, \
                                       weight_decay=L2_REG, momentum=MOMENTUM)
    criterion = AlphaLoss()

    for _ in range(epoch):
        for batch_idx, (state, move, winner) in enumerate(dataloader):
            if batch_idx % 10 == 1:
                print("batch index: %d loss: %.3f" \
                        % (batch_idx / 10, loss))
            example = {
                'state': Variable(state).type(DTYPE_FLOAT),
                'winner': Variable(winner).type(DTYPE_FLOAT),
                'move' : Variable(move).type(DTYPE_FLOAT if NO_MCTS else DTYPE_LONG)
            }
            loss = train_epoch(player, optimizer, example, criterion)
    
    return player, optimizer