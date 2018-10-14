from __future__ import print_function, division

from osgeo import gdal, gdal_array
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm

from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn import svm

from sklearn.metrics import accuracy_score
from sklearn.metrics import precision_score
from sklearn.metrics import recall_score
from sklearn.metrics import cohen_kappa_score
from sklearn.metrics import confusion_matrix

gdal.UseExceptions()
gdal.AllRegister()

'''
#SAFE format files are preprocessed and created using Sentinel-1 ToolBox 
#Preprocessing steps include:
1. Multilooking - 3x3 window
2. Calibration
3. Range Doppler Terrain Correction - Bilinear Interpolation
4. Crop to study area
5. Convert data type to uint8
#Creating training and testing label masks 
#Export as GeoTiff Image
#Image includes training and testing label masks as bands
'''

#Read GeoTiff file using GDAL 
img_ds = gdal.Open('31_10_Cnv.tif', gdal.GA_ReadOnly)
num_bands = 6

'''
Bands in processed data:
1 : Sigma0_VH
2 : Gamma0_VH
3 : Beta0_VH
4 : Sigma0_VV
5 : Gamma0_VV
6 : Beta0_VV
'''

print(img_ds.RasterCount)
img = np.zeros((img_ds.RasterYSize, img_ds.RasterXSize, img_ds.RasterCount-8), gdal_array.GDALTypeCodeToNumericTypeCode(img_ds.GetRasterBand(1).DataType))

for b in range(num_bands):
	img[:,:,b] = img_ds.GetRasterBand(b+1).ReadAsArray()

#Training mask:
roi1 = img_ds.GetRasterBand(7).ReadAsArray().astype(np.uint8)/255 * 10#urban
roi2 = img_ds.GetRasterBand(9).ReadAsArray().astype(np.uint8)/255 * 50 #water
roi3 = img_ds.GetRasterBand(11).ReadAsArray().astype(np.uint8)/255 * 100 #veg
roi4 = img_ds.GetRasterBand(13).ReadAsArray().astype(np.uint8)/255 * 150 #open
roi = roi1 + roi2 + roi3 + roi4

#Test mask:
roi1_test = img_ds.GetRasterBand(10).ReadAsArray().astype(np.uint8)/255 * 10 #urban
roi2_test = img_ds.GetRasterBand(8).ReadAsArray().astype(np.uint8)/255 * 50 #water
roi3_test = img_ds.GetRasterBand(12).ReadAsArray().astype(np.uint8)/255 * 100 #veg
roi4_test = img_ds.GetRasterBand(14).ReadAsArray().astype(np.uint8)/255 * 150 #open
roi_test = roi1_test + roi2_test + roi3_test + roi4_test

labels = np.unique(roi[roi>0])
print('The training data includes {n} classes: {classes}'.format(n=labels.size,classes=labels))

#Training data set creation
X = img[roi > 0, :]
y = roi[roi > 0]

#Testing data set creation 
X_test = img[roi_test > 0, :]
y_test = roi_test[roi_test > 0]

print('Number of training and test points:')
print('Training data size: {sz}'.format(sz=X.shape))
print('Training labels vector length: {sz}'.format(sz=y.shape))
print('Testing data size: {sz}'.format(sz=X_test.shape))
print('Testing labels vector length: {sz}'.format(sz=y_test.shape))

### Train classifier using training pixels ###
#rf = RandomForestClassifier(n_estimators=500, oob_score=True)
#mlp =  MLPClassifier(hidden_layer_sizes=(100,50), max_iter=100, alpha=1e-4, solver='adam', verbose=10, tol=1e-4, random_state=1, learning_rate_init=1e-5)
svc = svm.SVC()

#rf = rf.fit(X,y)
#mlp = mlp.fit(X,y)
svc = svc.fit(X,y)
#print('OOB prediction of accuracy is: {oob}%'.format(oob=rf.oob_score_ * 100))

### Test the classifier model using test data ###
#pred = rf.predict(X_test)
#pred = mlp.predict(X_test)
pred = svc.predict(X_test)


### Calculate metrics ###
acc = accuracy_score(y_test, pred)
prec = precision_score(y_test, pred, average='micro')
recall = recall_score(y_test, pred, average='micro')
kappa = cohen_kappa_score(y_test, pred)
cm = confusion_matrix(y_test, pred)

print('Accuracy : {acc}%'.format(acc=acc))
print('Precision : {prec}%'.format(prec=prec))
print('Recall : {rec}%'.format(rec=recall))
print('Kappa Score : {kappa}%'.format(kappa=kappa))
print('Confusion matrix')
print('{cm}'.format(cm=cm))

###Print importance of bands ###
#bands = np.arange(num_bands)
#for b, imp in zip(bands, rf.feature_importances_):
#	    print('Band {b} importance: {imp}'.format(b=b, imp=imp))
'''
### Generate classification map ###
new_shape = (img.shape[0]*img.shape[1], img.shape[2])
img_as_array = img[:,:,:num_bands].reshape(new_shape)

class_prediction = rf.predict(img_as_array)
#class_prediction = mlp.predict(img_as_array)
#class_prediction = svc.predict(img_as_array)
class_prediction = class_prediction.reshape(img[:,:,0].shape)
class_prediction = class_prediction.astype(np.uint8)
np.save('cp.npy', class_prediction)

print('Water pixels: {water}'.format(water=np.sum(class_prediction==50))) 
print('Urban pixels: {urb}'.format(urb=np.sum(class_prediction==10)))
print('Veg pixels: {veg}'.format(veg=np.sum(class_prediction==100)))
print('Open pixels: {op}'.format(op=np.sum(class_prediction==150)))
n = class_prediction.max()
# Next setup a colormap for our map
#colors = dict((
#    (0, (0, 0, 0, 255)),  # Nodata
#    (100, (0, 150, 0, 255)),  # Forest
#    (50, (0, 0, 255, 255)),  # Water
#    #(0, (0, 255, 0, 255)),  # Herbaceous
#    (150, (160, 82, 45, 255)),  # Barren
#    (10, (255, 0, 0, 255))  # Urban
#))
# Put 0 - 255 as float 0 - 1
#for k in colors:
#    v = colors[k]
#    _v = [_v / 255.0 for _v in v]
#    colors[k] = _v
    
#index_colors = [colors[key] if key in colors else 
#                (0, 0, 0, 0) for key in range(1, n + 1)]
#cmap = plt.matplotlib.colors.ListedColormap(index_colors, 'Classification', n)
#

plt.plot
plt.imshow(class_prediction)
plt.show()
'''





