import torch
from torch import nn
import argparse
import utils
from utils import DataHandler
from model import SPINEModel
from random import shuffle
import numpy as np
import logging
logging.basicConfig(level=logging.INFO)


#########################################################

parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

parser.add_argument('--hdim', dest='hdim', type=int, default=500,
                    help='resultant embedding size')

parser.add_argument('--h2dim', dest='h2dim', type=int, default=1000,
                    help='resultant embedding size')

parser.add_argument('--denoising', dest='denoising',
					default=False,
					action='store_true',
                    help='noise amount for denoising auto-encoder')

parser.add_argument('--noise', dest='noise_level', type=float,
					default=0.2,
                    help='noise amount for denoising auto-encoder')

parser.add_argument('--num_epochs', dest='num_epochs', type=int,
					default=500,
                    help='number of epochs')

parser.add_argument('--batch_size', dest='batch_size', type=int,
					default=64,
                    help='batch size')

parser.add_argument('--sparsity', dest='sparsity', type=float,
					default=0.85,
                    help='sparsity')

parser.add_argument('--input', dest='input',
					default = "glove300d.txt" ,
                    help='input src')

parser.add_argument('--output', dest='output',
					default = "glove2d1.spine" ,
                    help='output')

#########################################################

class Solver:

	def __init__(self, params):

		# Build data handler
		self.data_handler = DataHandler()
		self.data_handler.loadData(params['input'])
		params['inp_dim'] = self.data_handler.getDataShape()[1]
		logging.info("="*41)


		# Build model
		self.model = SPINEModel(params)
		self.dtype = torch.FloatTensor
		use_cuda = torch.cuda.is_available()
		if use_cuda:
			self.model.cuda()
			self.dtype = torch.cuda.FloatTensor
		self.optimizer = torch.optim.SGD(self.model.parameters(), lr=0.1)
		logging.info("="*41)


	def train(self, params):
		num_epochs, batch_size = params['num_epochs'], params['batch_size'],
		optimizer = self.optimizer
		dtype = self.dtype
		for iteration in range(num_epochs):
			self.data_handler.shuffleTrain()
			num_batches = self.data_handler.getNumberOfBatches(batch_size)
			epoch_losses = np.zeros(4) # rl, asl, psl, total
			for batch_idx in range(num_batches):
				optimizer.zero_grad()
				batch_x, batch_y = self.data_handler.getBatch(batch_idx, batch_size, params['noise_level'], params['denoising'] )
				batch_x = torch.from_numpy(batch_x).type(dtype)
				batch_y = torch.from_numpy(batch_y).type(dtype)
				out, h, loss, loss_terms = self.model(batch_x, batch_y)
				reconstruction_loss, psl_loss, asl_loss = loss_terms
				loss.backward()
				optimizer.step()
				epoch_losses[0]+=reconstruction_loss.item()
				epoch_losses[1]+=asl_loss.item()
				epoch_losses[2]+=psl_loss.item()
				epoch_losses[3]+=loss.item()
			print("After epoch %r, Reconstruction Loss = %.4f, ASL = %.4f,"\
						"PSL = %.4f, and total = %.4f"
						%(iteration+1, epoch_losses[0], epoch_losses[1], epoch_losses[2], epoch_losses[3]) )
			#logging.info("After epoch %r, Sparsity = %.1f"
			#			%(iteration+1, utils.compute_sparsity(h.cpu().data.numpy())))
				#break
			#break

	def getSpineEmbeddings(self, batch_size, params):
		ret = []
		self.data_handler.resetDataOrder()
		num_batches = self.data_handler.getNumberOfBatches(batch_size)
		for batch_idx in range(num_batches):
			batch_x, batch_y = self.data_handler.getBatch(batch_idx, batch_size, params['noise_level'], params['denoising'] )
			batch_x = torch.from_numpy(batch_x).type(self.dtype)
			batch_y = torch.from_numpy(batch_y).type(self.dtype)
			_, h, _, _ = self.model(batch_x, batch_y)
			ret.extend(h.cpu().data.numpy())
		return np.array(ret)

	def getWordsList(self):
		return self.data_handler.getWordsList()


#########################################################

def main():
	device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
	params = vars(parser.parse_args())
	#params.to(device)
	logging.info("PARAMS = " + str(params))
	logging.info("="*41)
	solver = Solver(params)
	#solver.to(device)
	solver.train(params)
		
	# dumping the final vectors
	logging.info("Dumping the final SPine embeddings")
	output_path = params['output'] #+ ".spine"
	final_batch_size = 512
	spine_embeddings = solver.getSpineEmbeddings(final_batch_size, params)
	utils.dump_vectors(spine_embeddings, output_path, solver.getWordsList())


if __name__ == '__main__':
	main()
