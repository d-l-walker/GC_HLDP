import os
import shutil
import logging
import numpy as np
import pandas as pd
import astropy.units as u


# Function to modify the uid string to be compatible with the file naming convention
def modify_uid(uid_string):
    return uid_string.replace('://', '___').replace('/', '_')


if os.path.exists('moment_movie_script.log'):
    os.remove('moment_movie_script.log')

logging.basicConfig(filename='moment_movie_script.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

make_moments = True
make_movies = True

df = pd.read_csv('chans.csv')
df['mol'] = df['mol'].str.replace(' ', '_').str.replace('(', '').str.replace(')', '')

# Loop through each row in and create moment maps and movies
for index, row in df.iterrows():
    modified_uid = modify_uid(row['uid'])
    search_str = "*{}*{}*.fits".format(row['name'], modified_uid)
    matching_files = [f for f in os.listdir() if all(s in f for s in [row['name'], modified_uid]) and f.endswith('.fits')]
    
    for file in matching_files:
        os.makedirs(row['project'], exist_ok=True)
        mol = row['mol']
        if pd.isna(row['chans']):
            continue
        start, end = [int(x) for x in row['chans'].split('~')]

        # Get the start and end frequencies from the fits file based on the channel range
        file_ok = True
        try:
            ia.open(file)
            cs = ia.coordsys()
            start_freq = ((cs.toworld([0,0,start,0])['numeric'][2])*u.Hz).to(u.GHz)
            end_freq = ((cs.toworld([0,0,end,0])['numeric'][2])*u.Hz).to(u.GHz)
            ia.close()
        # Sometimes downloads fail and the fits file is corrupted. If this happens, skip the file and log the error
        except Exception as e:
            logging.error('Error: %s', e)
            logging.error('Error: %s', file)
            file_ok = False
        
        if file_ok:
            ext = '.moment0.integrated_{}-{}GHz'.format(np.around(start_freq.value, decimals=3), np.around(end_freq.value, decimals=3))
            
            if make_moments:
                outname_moments = file.replace('.fits', '.'+mol+ext)
                if not os.path.exists('./'+row['project']+'/'+outname_moments+'.fits'):
                    immoments(imagename=file,
                            moments=[0],
                            axis='spectral',
                            chans=str(start)+'~'+str(end),
                            outfile='./'+row['project']+'/'+outname_moments)

                    exportfits(imagename='./'+row['project']+'/'+outname_moments, fitsimage='./'+row['project']+'/'+outname_moments+'.fits', overwrite=True)
                    
                    try:
                        path = os.path.join(row['project'], outname_moments)
                        shutil.rmtree(path)
                    except OSError as e:
                        logging.error(f"Error: {e.filename} - {e.strerror}.")
                else:
                    logging.info('Moment map already exists: %s', outname_moments)

            if make_movies:
                outname_movie = file.replace('.fits', '.'+mol+ext+'.mp4')
                if not os.path.exists('./'+row['project']+'/'+outname_movie):
                    importfits(fitsimage=file, imagename=file.replace('.fits', '.image'), overwrite=True)
                    if os.path.isdir('./temp'):
                        shutil.rmtree('./temp')

                    os.makedirs('temp', exist_ok=True)

                    for chan in range(start, end):
                        imsubimage(imagename=file.replace('.fits', '.image'), outfile='./temp/'+str(chan)+'.image', chans=str(chan), overwrite=False)

                    for chan in range(start, end):
                        chan_image = "./temp/" + str(chan) + ".image"
                        chan_png = "./temp/" + str(chan) + ".png"
                        imview(raster=chan_image, out=chan_png)

                    os.system('ffmpeg -framerate 10 -start_number ' + str(start) + ' -i ./temp/%d.png ' + './'+row['project']+'/'+outname_movie)
                else:
                    logging.info('Movie already exists: %s', outname_movie)

            if os.path.isdir('./temp'):
                logging.info('Cleaning up temp directory')
                shutil.rmtree('./temp')
            if file:
                file_to_remove = file.replace('.fits', '.image')
                if os.path.isdir(file_to_remove):
                    logging.info('Cleaning up image files')
                    shutil.rmtree(file_to_remove)