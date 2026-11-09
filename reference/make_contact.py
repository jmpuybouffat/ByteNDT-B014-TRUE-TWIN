exec(open('/workspace/C1_contact_coupe/export_contact.py').read().split('pa=np.array')[0])
reg=json.load(open('/workspace/C1_gorge_correction/REGISTRATION_C1.json'));rows=list(csv.DictReader((ROOT/'assets/C1_3485_LOIS_FOCALES.csv').open()));motion=[];previous_normal=None;previous_across=None
for i,f in enumerate(reg['motion']):
 c=np.array(f['contact']);n=np.array(f['normal']);T=np.array(f['T']);R=np.array(f['R']);j=min(399,i);tan=np.array(reg['motion'][min(400,i+1)]['contact'])-np.array(reg['motion'][max(0,i-1)]['contact']);
 if previous_across is None:
  along=unit(tan-n*(tan@n));across=unit(np.cross(along,n))
 else:
  # Minimal rotation transports the mechanical foot frame with the surface
  # normal, rather than differentiating a contact curve with tiny reversals.
  k=np.cross(previous_normal,n);cs=float(np.clip(previous_normal@n,-1,1));sn=np.linalg.norm(k)
  if sn>1e-12:
   axis=k/sn;v=previous_across;across=v*cs+np.cross(axis,v)*sn+axis*(axis@v)*(1-cs)
  else:across=previous_across.copy()
  across=unit(across-n*(across@n))
 along=unit(np.cross(n,across));previous_normal=n.copy();previous_across=across.copy();grid=[];gf=[]
 for yy in np.linspace(-12.5,12.5,5):
  for xx in np.linspace(-12.5,12.5,5):
   desired=c+xx*across+yy*along;hh=hits(desired+n*50,-n);hh=[h for h in hh if abs(h[0]-50)<30];assert hh,(i,xx,yy);h=min(hh,key=lambda a:abs(a[0]-50));grid.append(h[2].tolist());gf.append(h[1])
 m={'phase':i/10,'shot':int(i/10)+1,'origin':f['origin'],'target':f['target'],'contact':f['contact'],'normal':f['normal'],'across':across.tolist(),'along':along.tolist(),'contact_triangle':f['contact_triangle'],'footprint':grid,'footprint_triangles':gf,'incidence_deg':f['incidence_deg']};motion.append(m)
frames=[]
for i in range(41):
 m=dict(motion[i*10]);m['shot']=i+1;f=reg['frames'][i];R=np.array(f['R']);T=np.array(f['T']);rays=[];origin=np.array(f['origin']);range0=f['source_range_mm']
 for row in rows[i*85:(i+1)*85]:
  dr=R@np.array([float(row['beam_ux']),float(row['beam_uy']),float(row['beam_uz'])]);rays.append({'entry':f['contact'],'dir':dr.tolist(),'end':(origin+dr*range0).tolist(),'sector':float(row['sector_deg']),'skew':float(row['skew_deg'])})
 m['rays']=rays;m['plane_normal']=unit(np.cross(np.array(m['target'])-origin,np.array(m['across']))).tolist();m['section']=[];frames.append(m)
out={'description':'Mechanical registration: first extrados groove and PA contact on original CAD mesh, interpolated normal central incidence55. Acoustic source matrices remain canonical; per-pose rigid coordinate reconstruction only, not a new physical UT validation.','frames':frames,'motion':motion};Path('/workspace/C1_contact_coupe/CONTACT_C1.json').write_text(json.dumps(out,separators=(',',':')))
print('401 registered contact poses and footprint grids generated')
