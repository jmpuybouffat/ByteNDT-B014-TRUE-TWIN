from pathlib import Path
import json,numpy as np
from scipy.interpolate import PchipInterpolator
r=Path('/workspace/LSB941-C1-PUBLICATION');s=(r/'assets/SCENE_C1_SYNCHRONISEE.html').read_text();D=json.JSONDecoder().raw_decode(s.split('const DATA=',1)[1])[0];old=json.load(open('/workspace/C1_gorge_correction/REGISTRATION_R2_AVANT_LISSAGE.json'));candidate=json.load(open('/workspace/C1_gorge_correction/REGISTRATION_CIBLE_LISSEE.json'));final=json.load(open('/workspace/C1_gorge_correction/TRAJET_LISSE_R3_FINAL.json'));assert final['optimizer_success'] and final['max_angle_error_deg']<1e-6 and final['late_reversals']==0
mot=final['motion'];oldpa=np.array(D['path']);oldt=np.array(D['targets'])
def unit(v):return v/max(np.linalg.norm(v),1e-20)
for i,f in enumerate(mot):
 if i<=280 or i>=399:mot[i]=old['motion'][i].copy();continue
 phase=i/10;k=min(39,int(phase));a=phase-k;p0=oldpa[k]*(1-a)+oldpa[k+1]*a;t0=oldt[k]*(1-a)+oldt[k+1]*a;d0=unit(t0-p0);q=np.array(f['target']);p=np.array(f['contact']);d=unit(q-p);Rbase=np.array(candidate['motion'][i]['R']);dbase=Rbase@d0;v=np.cross(dbase,d);cs=np.clip(dbase@d,-1,1);K=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]]);rot=np.eye(3)+K+K@K/max(1+cs,1e-15);R=rot@Rbase;dist=np.linalg.norm(t0-p0);origin=q-d*dist;T=origin-R@p0;f.update(R=R.tolist(),T=T.tolist(),origin=origin.tolist(),source_range_mm=float(dist),origin_contact_signed_offset_mm=float((p-origin)@d))
reg={**old,'method':'Late-course mechanical fairing constrained to actual mesh contact and central55deg to interpolated mesh normal; original UT replay reconstructed by proper rigid pose transforms. No new physical validation.','frames':mot[::10],'motion':mot,'smoothing':{'active_positions':[29,41],'first_and_last_contacts_held':True,'red_mechanical_groove_guide_unchanged':True,'focus_nominal_fairing_max_mm':float(np.max(np.linalg.norm(np.array([f['target']for f in mot])-np.array([f['target']for f in old['motion']]),axis=1))),'normal_model':'original interpolated mesh normals; no new acoustic model'}}
Path('/workspace/C1_gorge_correction/REGISTRATION_C1.json').write_text(json.dumps(reg,separators=(',',':')))
print('R3 registrations prepared; nominal focus fairing mm',reg['smoothing']['focus_nominal_fairing_max_mm'])
