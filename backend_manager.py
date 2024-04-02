# -*- coding: utf-8 -*-

import os 
import csv
import torch 
import torchaudio
import numpy as np
import torchaudio.transforms as transforms
from torch.cuda.amp import autocast
from src.models import ASTModel

os.environ['TORCH_HOME'] = './pretrained_models'
if os.path.exists('./pretrained_models') == False:
  os.mkdir('./pretrained_models')

"""
## Step 2. Create AST model and load AudioSet pretrained weights.
The pretrained model achieves 45.93 mAP on the AudioSet evaluation set, which is the best single model in the paper.
"""

# Create a new class that inherits the original ASTModel class
class ASTModelVis(ASTModel):
    def get_att_map(self, block, x):
        qkv = block.attn.qkv
        num_heads = block.attn.num_heads
        scale = block.attn.scale
        B, N, C = x.shape
        qkv = qkv(x).reshape(B, N, 3, num_heads, C // num_heads).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]  # make torchscript happy (cannot use tensor as tuple)
        attn = (q @ k.transpose(-2, -1)) * scale
        attn = attn.softmax(dim=-1)
        return attn
    def forward_visualization(self, x):
        # expect input x = (batch_size, time_frame_num, frequency_bins), e.g., (12, 1024, 128)
        x = x.unsqueeze(1)
        x = x.transpose(2, 3)
        B = x.shape[0]
        x = self.v.patch_embed(x)
        cls_tokens = self.v.cls_token.expand(B, -1, -1)
        dist_token = self.v.dist_token.expand(B, -1, -1)
        x = torch.cat((cls_tokens, dist_token, x), dim=1)
        x = x + self.v.pos_embed
        x = self.v.pos_drop(x)
        # save the attention map of each of 12 Transformer layer
        att_list = []
        for blk in self.v.blocks:
            cur_att = self.get_att_map(blk, x)
            att_list.append(cur_att)
            x = blk(x)
        return att_list
def make_features(wav_name, mel_bins, target_length=1024):
    waveform, sr = torchaudio.load(wav_name)
    if sr != 16000:
        resample = transforms.Resample(sr, 16000)
        waveform = resample(waveform)
        sr = 16000

    fbank = torchaudio.compliance.kaldi.fbank(
        waveform, htk_compat=True, sample_frequency=sr, use_energy=False,
        window_type='hanning', num_mel_bins=mel_bins, dither=0.0, frame_shift=10)

    n_frames = fbank.shape[0]

    p = target_length - n_frames
    if p > 0:
        m = torch.nn.ZeroPad2d((0, 0, 0, p))
        fbank = m(fbank)
    elif p < 0:
        fbank = fbank[0:target_length, :]

    fbank = (fbank - (-4.2677393)) / (4.5689974 * 2)
    return fbank


def load_label(label_csv):
    with open(label_csv, 'r') as f:
        reader = csv.reader(f, delimiter=',')
        lines = list(reader)
    labels = []
    ids = []  # Each label has a unique id such as "/m/068hy"
    for i1 in range(1, len(lines)):
        id = lines[i1][1]
        label = lines[i1][2]
        ids.append(id)
        labels.append(label)
    return labels

# Set Values that will be changed by GUI:
'''
Example inputs for the following functions:
label_csv = './egs/audioset/data/class_labels_indices.csv'
checkpoint_path = './pretrained_models/audio_mdl.pth'
audio_sample = './sample_audios/sample_audio2.mp3'


# Assume each input spectrogram has 1024 time frames
def load_model(checkpoint_path, input_tdim=1024):
    ast_mdl = ASTModelVis(label_dim=527, input_tdim=input_tdim, imagenet_pretrain=False, audioset_pretrain=False)
    print(f'[*INFO] load checkpoint: {checkpoint_path}')
    checkpoint = torch.load(checkpoint_path, map_location='cuda')
    audio_model = torch.nn.DataParallel(ast_mdl, device_ids=[0])
    audio_model.load_state_dict(checkpoint)
    audio_model = audio_model.to(torch.device("cuda:0"))
    audio_model.eval()
    return audio_model
'''
def load_model(checkpoint_path, input_tdim=1024):
    ast_mdl = ASTModelVis(label_dim=527, input_tdim=input_tdim, imagenet_pretrain=False, audioset_pretrain=False)
    print(f'[*INFO] load checkpoint: {checkpoint_path}')
    checkpoint = torch.load(checkpoint_path, map_location='cuda')
    audio_model = torch.nn.DataParallel(ast_mdl, device_ids=[0])
    audio_model.load_state_dict(checkpoint)
    audio_model = audio_model.to(torch.device("cuda:0"))
    audio_model.eval()
    return audio_model

'''
Example use: 
audio_model = load_model(checkpoint_path)
'''

"""## Step 3. Load an audio and predict the sound class.
By default we test one sample from another dataset (VGGSound) that has not been seen during the model training.
"""
def get_predictions(audio_model, label_csv, audio_sample, input_tdim=1024):
    
    # Load the AudioSet label set
    labels = load_label(label_csv)
    
    if os.path.exists('./sample_audios') == False:
      os.mkdir('./sample_audios')

    #wget.download(sample_audio_path, './sample_audios/sample_audio2.flac')
    feats = make_features(audio_sample, mel_bins=128)           # shape(1024, 128)

    feats_data = feats.expand(1, input_tdim, 128)           # reshape the feature
    feats_data = feats_data.to(torch.device("cuda:0"))

    # Make the prediction
    with torch.no_grad():
      with autocast():
        output = audio_model.forward(feats_data)
        output = torch.sigmoid(output)
    result_output = output.data.cpu().numpy()[0]
    sorted_indexes = np.argsort(result_output)[::-1]

    # Print audio tagging top probabilities
    predictions = ""
    for k in range(10):
        prediction = '- {}: {:.4f}\n'.format(np.array(labels)[sorted_indexes[k]], result_output[sorted_indexes[k]])
        predictions += prediction
    return predictions
'''
Example Usage:
predictions = get_predictions(audio_model, label_csv, audio_sample)
'''