# USGS GDB to topo SVG files

- We can download GDB files (ArcGIS file format, actually a directory of files) from [USGS](https://viewer.nationalmap.gov/basic/#productSearch)
- We read the GDB files with the open-source [GDAL package](https://gdal.org/)
  - This requires installing anaconda (miniconda) and then GDAL:
  ```
  conda install -c conda-forge gdal
  ```
- The data can then be parsed and detailed info dumped:
  - `ogrinfo -al` dumps all info
  ```
  ogrinfo -al ~/winHome/Documents/personal/topo_maps/VECTOR_Seattle_North_WA_7_5_Min_GDB.zip
  - `ogrinfo -so` provides a summary
  ```
  - Note: `ogrmerge` merges multiple vector datasets, may be useful

  - Providing the layer name gives detailed layer info:
  `ogrinfo ~/winHome/Documents/personal/topo_maps/VECTOR_Seattle_North_WA_7_5_Min_GDB.zip Elev_Contour`
  ```
- Creating the svg output uses the drawSvg package
  
