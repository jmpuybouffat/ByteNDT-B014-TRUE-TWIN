from pathlib import Path
import json,numpy as np
from scipy.spatial import cKDTree
r=Path('/workspace/LSB941-C1-PUBLICATION');s=(r/'assets/SCENE_C1_SYNCHRONISEE.html').read_text();D=json.JSONDecoder().raw_decode(s.split('const DATA=',1)[1])[0];tri=np.array(D['base'][0]['V']).reshape(-1,3,3);A,B,C=tri[:,0],tri[:,1],tri[:,2];E1=B-A;E2=C-A;N=np.cross(E1,E2);N/=np.maximum(np.linalg.norm(N,axis=1)[:,None],1e-30);oldp=np.array(D['path']);oldt=np.array(D['targets']);axis=np.array(json.load(open('/workspace/aube_positionnement_essai21/CENTRALE_CERCLES_ADAPTATIFS.json'))['basis'])[:,2]
def unit(v):return v/max(np.linalg.norm(v),1e-20)
def first_at(phase):
 i=min(39,int(phase));f=phase-i;p=oldt[i]*(1-f)+oldt[i+1]*f;n=unit(oldt[min(40,i+1)]-oldt[max(0,i-1)]);n[2]=0;n=unit(n);u=unit(np.cross(n,[0,0,1]));u*=np.sign(u@(oldp[i]-p));dd=(tri-p)@n;seg=[]
 # Vectorized mesh/plane intersections.
 pt=[[] for _ in range(len(tri))]
 for a,b in [(0,1),(1,2),(2,0)]:
  ids=np.where(dd[:,a]*dd[:,b]<0)[0];qq=tri[ids,a]+(dd[ids,a]/(dd[ids,a]-dd[ids,b]))[:,None]*(tri[ids,b]-tri[ids,a])
  for ix,q in zip(ids,qq):pt[ix].append(q)
 seg=np.array([q for q in pt if len(q)==2]);h=seg@axis;x=(seg-p)@u;hs=np.unique(h[(h>-1)&(h<7)])
 candidates=[]
 for z in hs:
  mask=(h[:,0]-z)*(h[:,1]-z)<=1e-13;den=h[:,1]-h[:,0];mask&=abs(den)>1e-10;ids=np.where(mask)[0];fac=(z-h[ids,0])/den[ids];xx=x[ids,0]+fac*(x[ids,1]-x[ids,0]);j=int(np.argmin(xx));q=seg[ids[j],0]+fac[j]*(seg[ids[j],1]-seg[ids[j],0]);candidates.append((xx[j],q))
 assert candidates,phase
 return max(candidates,key=lambda z:z[0])[1],u,n
# Full observed first-groove interval excludes the flat end face: geometry only.
oldp41=oldp.copy();oldt41=oldt.copy();phases=np.linspace(0,38,401);target=[];U=[];tangents=[]
for phase in phases:
 q,u,t=first_at(phase);target.append(q);U.append(u);tangents.append(t)
target=np.array(target)
oldp=np.column_stack([np.interp(np.linspace(0,40,401),np.arange(41),oldp41[:,j])for j in range(3)]);oldt=np.column_stack([np.interp(np.linspace(0,40,401),np.arange(41),oldt41[:,j])for j in range(3)])
# Contact is exactly on the mesh; the incidence reference is its interpolated
# area-weighted vertex normal, avoiding facet-normal jumps in a smooth airfoil.
from scipy.optimize import brentq
unique,inv=np.unique(np.round(tri.reshape(-1,3),5),axis=0,return_inverse=True);fi=inv.reshape(-1,3);vn=np.zeros_like(unique);area=np.cross(E1,E2)
for j in range(3):np.add.at(vn,fi[:,j],area)
vn/=np.maximum(np.linalg.norm(vn,axis=1)[:,None],1e-20)
def interp_normal(q,j):
 a=E1[j];b=E2[j];v=q-A[j];ab=a@b;den=(a@a)*(b@b)-ab*ab;x=((b@b)*(v@a)-ab*(v@b))/den;y=((a@a)*(v@b)-ab*(v@a))/den
 return unit(vn[fi[j,0]]*(1-x-y)+vn[fi[j,1]]*x+vn[fi[j,2]]*y)
contacts=[];normals=[];faces=[];reg=[];last=None;normal_errors=[]
for i,(q,u,tg) in enumerate(zip(target,U,tangents)):
 dd=(tri-q)@tg;pt=[[] for _ in tri]
 for a,b in [(0,1),(1,2),(2,0)]:
  ids=np.where(dd[:,a]*dd[:,b]<0)[0];qq=tri[ids,a]+(dd[ids,a]/(dd[ids,a]-dd[ids,b]))[:,None]*(tri[ids,b]-tri[ids,a])
  for j,v in zip(ids,qq):pt[j].append(v)
 candidates=[]
 for j,seg in enumerate(pt):
  if len(seg)!=2:continue
  a,b=seg;mid=(a+b)/2
  if not (20<mid[2]<180 and (mid-q)@u>20 and N[j]@u>.2):continue
  def fun(t):
   p=a+t*(b-a);n=interp_normal(p,j);return -n@unit(q-p)-np.cos(np.deg2rad(55))
  fa,fb=fun(0),fun(1)
  if fa*fb>0:continue
  f=brentq(fun,0,1,xtol=1e-13);p=a+f*(b-a);n=interp_normal(p,j);candidates.append((p,n,j))
 assert candidates,(i,'No smooth55contact')
 want=oldp[i]+q-oldt[i]
 def cost(c):return np.linalg.norm(c[0]-want)**2+(0 if last is None else np.linalg.norm(c[0]-last)**2*2)
 p,n,j=min(candidates,key=cost)
 # Preserve source beam/travel angle as well as local central incidence.
 from scipy.optimize import least_squares
 from scipy.signal import savgol_filter
 newtg=unit(savgol_filter(target,31,3,axis=0,deriv=1)[i]);oldtg=unit(oldt[min(400,i+1)]-oldt[max(0,i-1)]);oldD0=unit(oldt[i]-oldp[i]);skew0=oldD0@oldtg
 def surf(l,z):
  seed=q+tg*l+np.array([0.,0.,z])+u*200;dr=-u;h=np.cross(dr,E2);det=np.sum(E1*h,axis=1);iv=np.divide(1,det,out=np.zeros_like(det),where=abs(det)>1e-10);sv=seed-A;aa=iv*np.sum(sv*h,axis=1);qq=np.cross(sv,E1);bb=iv*np.sum(dr*qq,axis=1);rr=iv*np.sum(E2*qq,axis=1);ids0=np.where((abs(det)>1e-10)&(aa>=-1e-8)&(bb>=-1e-8)&(aa+bb<=1+1e-8)&(rr>0)&(N@u>.2))[0]
  if not len(ids0):raise ValueError('No airfoil point')
  k=ids0[np.argmin(rr[ids0])];v=seed+rr[k]*dr;return v,interp_normal(v,k),int(k)
 def fun(x):
  v,nn,k=surf(*x);dd=unit(q-v);return [-nn@dd-np.cos(np.deg2rad(55)),dd@newtg-skew0]
 guess=[(p-q)@tg,p[2]-q[2]]
 opt=least_squares(fun,guess,bounds=([-45,25],[45,190]),xtol=1e-11,ftol=1e-11,gtol=1e-11,max_nfev=100)
 assert max(abs(np.array(fun(opt.x))))<1e-5,(i,opt.x,fun(opt.x))
 p,n,j=surf(*opt.x);tg=newtg
 last=p;contacts.append(p);normals.append(n);faces.append(int(j));newD=unit(q-p);oldD=unit(oldt[i]-oldp[i]);oldU=oldtg;oldU=unit(oldU-oldD*(oldU@oldD));oldV=np.cross(oldD,oldU);newU=unit(tg-newD*(tg@newD));newV=np.cross(newD,newU);R=np.column_stack([newD,newU,newV])@np.column_stack([oldD,oldU,oldV]).T;oldrange=np.linalg.norm(oldt[i]-oldp[i]);origin=q-newD*oldrange;T=origin-R@oldp[i];reg.append({'shot':i/10+1,'R':R.tolist(),'T':T.tolist(),'contact':p.tolist(),'normal':n.tolist(),'contact_triangle':int(j),'target':q.tolist(),'origin':origin.tolist(),'incidence_deg':float(np.degrees(np.arccos(np.clip(-n@newD,-1,1)))),'source_range_mm':oldrange,'origin_contact_signed_offset_mm':float((p-origin)@newD)})
contacts=np.array(contacts);normal=np.array(normals);print('contact steps max',np.linalg.norm(np.diff(contacts,axis=0),axis=1).max());print('origin contact offsets',min(x['origin_contact_signed_offset_mm']for x in reg),max(x['origin_contact_signed_offset_mm']for x in reg));print('55 error',max(abs(x['incidence_deg']-55)for x in reg));out={'reference_depth_mm':27.6,'CAD_to_mm_scale':.1,'datum':'upper intrados platform corner; target middle of first extrados groove','method':'Mechanical pose registration of source acoustic replay; per-shot proper rigid transforms preserve source sound paths and phase laws. Not a new physical detection validation.','frames':reg[::10],'motion':reg};Path('/workspace/C1_gorge_correction/REGISTRATION_C1.json').write_text(json.dumps(out,separators=(',',':')))
np.savez('/workspace/C1_gorge_correction/geometry_first.npz',targets=target,contacts=contacts,normals=normal)
