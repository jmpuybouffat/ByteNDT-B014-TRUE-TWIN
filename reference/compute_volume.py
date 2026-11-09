from pathlib import Path
import os;os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import sys,json,csv,numpy as np,time,hashlib,base64
from skimage.measure import marching_cubes
ROOT=Path('/workspace/LSB941-C1-PUBLICATION');OUT=Path('/workspace/C1_beam_volume');src=(ROOT/'assets/SCENE_C1_SYNCHRONISEE.html').read_text();D=json.JSONDecoder().raw_decode(src.split('const DATA=',1)[1])[0]
rows=list(csv.DictReader((ROOT/'assets/C1_3485_LOIS_FOCALES.csv').open()));f=5.;c=3.23;omega=2*np.pi*f
# Source beam-frame axes are the same aperture axes used by C1 array_elements.
saxis=np.linspace(4.,125.,50);uaxis=np.linspace(-52.,52.,53);vaxis=np.linspace(-42.,42.,43);ss,uu,vv=np.meshgrid(saxis,uaxis,vaxis,indexing='ij');local=np.column_stack([ss.ravel(),uu.ravel(),vv.ravel()]);bank=[];check=[];start=time.time()
for shot in range(41):
 p=np.array(D['path'][shot]);t=np.array(D['targets'][shot]);beam=(t-p)/np.linalg.norm(t-p);tangent=np.array(D['path'][min(40,shot+1)])-np.array(D['path'][max(0,shot-1)]);U=tangent-beam*np.dot(tangent,beam);U/=np.linalg.norm(U);V=np.cross(beam,U);V/=np.linalg.norm(V);elements=np.array(D['elements'][shot]);lawrows=rows[shot*85:(shot+1)*85];delays=np.array([[float(r['delay_e%02d_us'%(j+1)])for j in range(64)]for r in lawrows]);law_beams=np.array([[float(r['beam_ux']),float(r['beam_uy']),float(r['beam_uz'])]for r in lawrows]);weights=np.exp(-1j*omega*delays).T
 q=p+local[:,0,None]*beam+local[:,1,None]*U+local[:,2,None]*V
 gains=np.empty(len(q));winner=np.empty(len(q),np.uint8)
 for begin in range(0,len(q),4096):
  qq=q[begin:begin+4096];dist=np.linalg.norm(qq[:,None,:]-elements[None,:,:],axis=2);phase=np.exp(-1j*(omega/c)*dist);gain=np.abs(phase@weights/64.)**2;directions=(qq-p)/np.maximum(np.linalg.norm(qq-p,axis=1)[:,None],1e-15);valid=(directions@law_beams.T)>=np.cos(np.deg2rad(14.));valid&=(np.linalg.norm(qq-p,axis=1)<=130)[:,None];gain=np.where(valid,gain,0.);winner[begin:begin+len(qq)]=gain.argmax(1);gains[begin:begin+len(qq)]=gain.max(1)
 assert gains.max()<=1+1e-10
 # Match the original source function at independently chosen nodes and laws.
 for index in [0,123,len(q)//2,len(q)-1]:
  li=int(winner[index]);dist=np.linalg.norm(q[index]-elements,axis=1);direct=abs(np.exp(-1j*omega*(delays[li]+dist/c)).sum()/64.)**2;direction=(q[index]-p)/np.linalg.norm(q[index]-p);direct=direct if direction@law_beams[li]>=np.cos(np.deg2rad(14.)) and np.linalg.norm(q[index]-p)<=130 else 0.;check.append(abs(direct-gains[index]))
 db=np.maximum(-60,10*np.log10(np.maximum(gains,1e-12))).reshape(ss.shape);np.savez_compressed(OUT/('volume_%02d.npz'%(shot+1)),db=db.astype(np.float32),winner=winner.reshape(ss.shape),origin=p,basis=np.array([beam,U,V]),s=saxis,u=uaxis,v=vaxis)
 meshes={}
 for level in [-6.,-12.]:
  if db.min()<level<db.max():
   verts,faces,_,_=marching_cubes(db.astype(np.float32),level,spacing=(saxis[1]-saxis[0],uaxis[1]-uaxis[0],vaxis[1]-vaxis[0]),allow_degenerate=False)
   verts+=np.array([saxis[0],uaxis[0],vaxis[0]])
   meshes[str(int(level))]={'vertices':base64.b64encode(np.rint(verts*100).astype('<i2').tobytes()).decode(),'faces':base64.b64encode(faces.astype('<u2').tobytes()).decode(),'encoding':'int16_xyz_0.01mm_uint16_faces','vertices_count':len(verts),'triangles_count':len(faces)}
 quant=np.rint((db.ravel()+60)*4).clip(0,240).astype(np.uint8)
 bank.append({'shot':shot+1,'origin':p.tolist(),'basis':np.array([beam,U,V]).tolist(),'dbq':base64.b64encode(quant.tobytes()).decode(),'meshes':meshes})
 print('Computed',shot+1,'/41',round(time.time()-start,1),'s',flush=True)
meta={'quantity':'C1 coherent-array sensitivity, max of 85 original laws within original 14-degree angular acceptance and 130mm range; not calibrated pressure','db_definition':'10 log10(max_law(vectorized_coherent_gain)), fixed unity reference; original angular acceptance retained','frequency_MHz':f,'shear_speed_mm_us':c,'elements':64,'laws_per_position':85,'shape':list(ss.shape),'axes':{'s':saxis.tolist(),'u':uaxis.tolist(),'v':vaxis.tolist()},'frames':bank}
(OUT/'C1_COHERENT_VOLUME.json').write_text(json.dumps(meta,separators=(',',':')))
audit={'source_function':'B014_TRUE_TWIN_LIVING_ENGINEERING_FINAL.py::vectorized_coherent_gain','source_delays_csv_sha256':hashlib.sha256((ROOT/'assets/C1_3485_LOIS_FOCALES.csv').read_bytes()).hexdigest(),'positions':41,'laws_per_position':85,'elements':64,'shape':list(ss.shape),'grid_step_mm':[float(saxis[1]-saxis[0]),float(uaxis[1]-uaxis[0]),float(vaxis[1]-vaxis[0])],'maximum_source_function_difference':float(max(check)),'voxel_count':len(q),'no_hand_drawn_envelope':True,'scattering_models_recomputed':False,'quantity':'coherent-array sensitivity within original source acceptance, not calibrated pressure','viewer_quantization_db':.25};(OUT/'CONTROLE_VOLUME_CALCULE.json').write_text(json.dumps(audit,indent=2));print('DONE',audit)
