#!/usr/bin/python

import sa_library.readinsight3 as readinsight3
import sys
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib import rc
import numpy as np
import scipy.ndimage
import matplotlib.cm as cm

# def find_nearest(array,value):
#         idx = (np.abs(array-value)).argmin()
#         return [array[idx],idx]

rc('font', **{'family':'serif','serif':['Palatino']})
rc('text', usetex=True)

shape = np.array([191,183])
px_size = 133                 # pixel size in the source images, in nm
render_px = 20                # pixel size in the final image, in nm
shape = px_size*shape         # shape conversion to um

i3_data_in = readinsight3.loadI3GoodOnly(sys.argv[1])
x_locs = i3_data_in['xc']*px_size                 # px -> um conversion
y_locs = i3_data_in['yc']*px_size
fit_error = i3_data_in['i']
fit_sigma = 0.5*i3_data_in['w']     # 0.5 factor to turn the width of the gaussian into a sigma
n_photons = i3_data_in['a']

# LOCALIZATION BINNING
H, xedges, yedges = np.histogram2d(0.001*y_locs, 0.001*x_locs, bins=np.ceil(shape/render_px))
extent = [yedges[0], yedges[-1],  xedges[0], xedges[-1]]
# Herror, Herror_bins = np.histogram(fit_error,bins=100)

# IMAGE SAVING
scipy.misc.imsave('out.png', H)

# FIGURE CREATION
fig = plt.figure(figsize=(17.0, 7.0))
gs = gridspec.GridSpec(3, 2)

# PLOT THE RESULTING IMAGE
ax1 = plt.subplot(gs[:,0])
img = ax1.imshow(H, extent=extent, cmap='gray', vmax = 10, interpolation='none')
plt.xlabel('$\mu$m')
plt.ylabel('$\mu$m')
fig.colorbar(img, ax=ax1)
ax1.axis('image')

# PROFILE ATTEMPT (NOT WORKING CORRECTLY)
# punto1 = find_nearest(xedges,4.5)[1],find_nearest(yedges,10)[1]
# punto2 = find_nearest(xedges,5.2)[1],find_nearest(yedges,8.6)[1]
# length = int(np.hypot(punto2[0]-punto1[0], punto2[1]-punto1[1]))
# length = 1000000
# lin_x, lin_y = np.linspace(punto1[0], punto2[0], length), np.linspace(punto1[1], punto2[1], length)
# profile = H[lin_x.astype(np.int), lin_y.astype(np.int)]
# # profile = scipy.ndimage.map_coordinates(H, np.vstack((lin_x,lin_y)))
# axes[0].plot([punto1[0], punto2[0]], [punto1[1], punto2[1]], 'ro-')
# ax1.plot([4.5, 5.2], [10, 8.6], 'ro-')

# ERROR HISTOGRAM
ax2 = plt.subplot(gs[0,1])
plt.hist(fit_error, bins=np.arange(0,200))
plt.xlabel('Fit error [nm?]')
plt.grid(True)

ax3 = plt.subplot(gs[1,1])
plt.hist(fit_sigma, bins=np.arange(50,300))
plt.xlabel('Fit sigma [nm?]')
plt.grid(True)

ax4 = plt.subplot(gs[2,1])
plt.hist(n_photons, bins=np.arange(0,3000), histtype='step')
plt.xlabel('Number of photons per localization')
plt.grid(True)


plt.tight_layout()
plt.show()
