from qgis import processing
from qgis.processing import alg
from qgis.core import QgsProcessingFeedback

@alg(name='slopealg', label='Slope Computation and Vectorization (alg)',
     group='myscripts', group_label='My scripts')
     
@alg.input(type=alg.MULTILAYER, name='INPUT', label='Input DEM(s)')

@alg.input(type=alg.RASTER_LAYER_DEST, name='MOSAICKED',
           label='Mosaicked DEM (save as .sdat)')
           
@alg.input(type=alg.RASTER_LAYER_DEST, name='RESAMPLED',
           label='Resampled DEM (save as .sdat)')
        
@alg.input(type=alg.RASTER_LAYER_DEST, name='SLOPE',
           label='Slope (save as .tif)')

@alg.input(type=alg.RASTER_LAYER_DEST, name='CLASSEDSLOPE',
           label='Classed slope (save as .sdat)')
           
@alg.input(type=alg.VECTOR_LAYER_DEST, name='VECTORSLOPE',
           label='Vectorized slope (save as .shp)')
           
@alg.input(type=alg.NUMBER, name='ORIGINALGRAIN', label='Input DEM grain (m)',
           default=1.0)
           
@alg.input(type=alg.NUMBER, name='DESIREDGRAIN', label='Desired grain (m)',
           default=2.0)

def slopealg(instance, parameters, context, feedback, inputs):
    """
    This tool performs slope computation, classification, and vectorization for a set of one or more DEMs.
    Warning: Do not use temporary outputs or the algorithm may not finish running.
    
    Author: Maja Cannavo, 2020
    """

    # mosaic DEMs

    mosaicked_result = processing.run("saga:mosaicrasterlayers", # SAGA Mosaic Raster Layers tool
        {'GRIDS':parameters['INPUT'], # input grids
        'NAME':'Mosaic',
        'TYPE':7, # data storage type: 4 byte floating point
        'RESAMPLING':1, # bilinear interpolation
        'OVERLAP':4, # overlapping areas: mean
        'BLEND_DIST':8,# blend distance: 8m
        'MATCH':0, # match: none
        'TARGET_USER_XMIN TARGET_USER_XMAX TARGET_USER_YMIN TARGET_USER_YMAX':None, # optional output extent
        'TARGET_USER_SIZE':parameters['ORIGINALGRAIN'], # raw DEM grain size
        'TARGET_USER_FITS':1, # fit to cells
        'TARGET_OUT_GRID':parameters['MOSAICKED']}, # where to save output
        is_child_algorithm=True,
        context=context,
        feedback=feedback) 
    
    if feedback.isCanceled():
        return {}
    
    feedback.setProgressText('Mosaicking finished')
    
    
     # resample mosaicked DEM, if necessary

    if parameters['ORIGINALGRAIN'] != parameters['DESIREDGRAIN']:
        resampled_result = processing.run("saga:resampling", # SAGA resampling tool
            {'INPUT':mosaicked_result['TARGET_OUT_GRID'], # input grid
            'KEEP_TYPE':True, # preserve data type
            'SCALE_UP':3, # B-spline interpolation
            'SCALE_DOWN':3, # B-spline interpolation
            'TARGET_USER_XMIN TARGET_USER_XMAX TARGET_USER_YMIN TARGET_USER_YMAX':None, # optional output extent
            'TARGET_USER_SIZE':parameters['DESIREDGRAIN'], # new grain size
            'TARGET_USER_FITS':1, # fit to cells
            'TARGET_TEMPLATE':None, # optional target system
            'OUTPUT':parameters['RESAMPLED']}, # where to save output
            is_child_algorithm=True,
            context=context,
            feedback=feedback)
        
        resampled_output = resampled_result['OUTPUT']
        
    else:
        resampled_output = mosaicked_result['TARGET_OUT_GRID']
    
    if feedback.isCanceled():
        return {}
    
    feedback.setProgressText('Resampling finished')
        
   
    # compute slope
    
    slope_result = processing.run("gdal:slope",  # GDAL slope tool
        {'INPUT':resampled_output, # input layer
        'BAND':1, # band number
        'SCALE':1, # ratio of vertical units to horizontal
        'AS_PERCENT':True, # express as percent instead of degrees
        'COMPUTE_EDGES':False, # do not compute edges
        'ZEVENBERGEN':False, # do not use ZevenbergenThorne formula
        'OPTIONS':'', # optional additional creation options
        'EXTRA':'', # optional additional command-line parameters
        'OUTPUT':parameters['SLOPE']}, # where to save output
        is_child_algorithm=True,
        context=context,
        feedback=feedback)
    
    slope_output = slope_result['OUTPUT']
    
    if feedback.isCanceled():
        return{}
    
    feedback.setProgressText('Slope calculated')


    # classify slope using SAGA raster calculator
    classed_slope_result = processing.run("saga:rastercalculator", 
        {'GRIDS':slope_output, # input layer
        'XGRIDS':'', # additional layers (optional)
        'FORMULA':'(or(gt(a,0),eq(a,0)))+\
            (or(gt(a,5),eq(a,5)))+\
            (or(gt(a,10),eq(a,10)))+\
            (or(gt(a,15),eq(a,15)))+\
            (or(gt(a,20),eq(a,20)))+\
            (or(gt(a,30),eq(a,30)))',
        'RESAMPLING':3, # B-spline interpolation
        'USE_NODATA':False, # do not use NoData
        'TYPE':7, # output data type: 4-byte floating point
        'RESULT':parameters['CLASSEDSLOPE']}, # where to save output
        is_child_algorithm=True,
        context=context,
        feedback=feedback)
    
    classed_slope_output = classed_slope_result['RESULT']
    
    if feedback.isCanceled():
        return{}
    
    feedback.setProgressText('Slope classified')

    
    # vectorize classed slope

    vector_slope_result = processing.run("gdal:polygonize",
        {'INPUT':classed_slope_output, # input layer
        'BAND':1, # band number
        'FIELD':'class', # name of the field to create
        'EIGHT_CONNECTEDNESS':False, # do not use 8-connectedness
        'EXTRA':'', # additional command-line parameters (optional)
        'OUTPUT':parameters['VECTORSLOPE']}, # where to save output
        is_child_algorithm=True,
        context=context,
        feedback=feedback)

    if feedback.isCanceled():
        return{}
    
    feedback.setProgressText('Slope vectorized')
    
    
    # return results
    
    return {'MOSAICKED':mosaicked_result['TARGET_OUT_GRID'],
        'RESAMPLED':resampled_output,
        'SLOPE':slope_output,
        'CLASSEDSLOPE':classed_slope_output,
        'VECTORSLOPE':vector_slope_result['OUTPUT']}