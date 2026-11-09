from pathlib import Path
exec(Path('/workspace/C1_gorge_correction/lisser_final.py').read_text().split("print('Optimizing'")[0])
from scipy.optimize import minimize
active=np.arange(1,m-2);na=len(active);xbase=x0.copy();oldglob=json.load(open('/workspace/C1_gorge_correction/TRAJET_LISSE_FINAL.json'));PP=np.array([f['contact']for f in oldglob['motion']])[I];xx=np.column_stack([np.sum((PP-q)*tg,axis=1),PP[:,2]-q[:,2]]);xx[[0,-2,-1]]=x0[[0,-2,-1]]
def unpack(y):x=xbase.copy();x[active]=np.reshape(y,(na,2));return x
def surface_jac(y):
 X=unpack(y);vals=coef0+X[:,0,None,None]*coefL+X[:,1,None,None]*coefZ;aa,bb,rr=vals[:,:,0],vals[:,:,1],vals[:,:,2];valid=normalmask&(aa>=-1e-7)&(bb>=-1e-7)&(aa+bb<=1+1e-7)&(rr>0);face=np.argmin(np.where(valid,rr,np.inf),axis=1);ix=np.arange(m);a=aa[ix,face];b=bb[ix,face];p=base+tg*X[:,0,None]+np.array([0,0,1])*X[:,1,None]+dr*rr[ix,face,None];v0=vn[fi[face,0]];v1=vn[fi[face,1]];v2=vn[fi[face,2]];raw=v0*(1-a-b)[:,None]+v1*a[:,None]+v2*b[:,None];nn=np.linalg.norm(raw,axis=1);n=raw/nn[:,None];DP=[];DN=[]
 for coef,seed in [(coefL,tg),(coefZ,np.broadcast_to([0,0,1],(m,3)))]:
  cf=coef[ix,face];dp=seed+dr*cf[:,2,None];dn0=(v1-v0)*cf[:,0,None]+(v2-v0)*cf[:,1,None];dn=(dn0-n*np.sum(n*dn0,axis=1)[:,None])/nn[:,None];DP.append(dp);DN.append(dn)
 return p,n,face,np.stack(DP,axis=2),np.stack(DN,axis=2)
def equality(y,grad=False):
 p,n,f,dp,dn=surface_jac(y);vec=q-p;length=np.linalg.norm(vec,axis=1);d=vec/length[:,None];val=-np.sum(n*d,axis=1)-np.cos(np.deg2rad(55));
 if not grad:return val[active]*100
 dd=(-dp+d[:,:,None]*np.einsum('ij,ijk->ik',d,dp)[:,None,:])/length[:,None,None];jac=-np.einsum('ijk,ij->ik',dn,d)-np.einsum('ij,ijk->ik',n,dd);J=np.zeros((na,na,2));J[np.arange(na),np.arange(na)]=jac[active];return J.reshape(na,na*2)*100
def objective(y,grad=False):
 p,n,f,dp,dn=surface_jac(y);allp=np.vstack([prefix,p]);dd=np.diff(allp,n=2,axis=0);vel=np.diff(np.vstack([P[start-1],p]),axis=0);diff=vel-vpreferred[start-1:];progress=np.sum(vel*guide[start-1:],axis=1);hinge=np.minimum(progress-.08,0);a=.2;beta=100.;eta=10.;kap=300.;delta=p-pref[I];val=a*a*np.sum(delta*delta)+beta*beta*np.sum(dd*dd)+eta*eta*np.sum(diff*diff)+kap*kap*np.sum(hinge*hinge)
 if not grad:return val/10000
 g=2*a*a*delta;g+=2*beta*beta*dd;g[:-1]-=4*beta*beta*dd[1:];g[:-2]+=2*beta*beta*dd[2:];gv=2*eta*eta*diff+2*kap*kap*hinge[:,None]*guide[start-1:];g+=gv;g[:-1]-=gv[1:];return np.einsum('ij,ijk->ik',g,dp)[active].ravel()/10000
y=xx[active].ravel();print('SLSQP',na,'constrained surface poses',flush=True)
res=minimize(objective,y,jac=lambda z:objective(z,True),method='SLSQP',constraints=[{'type':'eq','fun':equality,'jac':lambda z:equality(z,True)}],bounds=list(zip(lo[active].ravel(),hi[active].ravel())),options={'ftol':1e-9,'maxiter':600,'disp':False})
p,n,f,_,_=surface_jac(res.x);Q=P.copy();Q[I]=p;D=Qtar[I]-p;D/=np.linalg.norm(D,axis=1)[:,None];ang=np.degrees(np.arccos(np.clip(-np.sum(n*D,axis=1),-1,1)));v=np.diff(Q,axis=0)
def turns(v):return np.degrees(np.arccos(np.clip(np.sum(v[:-1]*v[1:],axis=1)/np.maximum(np.linalg.norm(v[:-1],axis=1)*np.linalg.norm(v[1:],axis=1),1e-15),-1,1)))
print('result',res.message,res.nit,'angle err',max(abs(ang-55)),'maxmove',np.linalg.norm(Q-P,axis=1).max(),'maxturn',turns(v)[start:].max(),'reversals',sum(turns(v)[start:]>90),'late length',np.linalg.norm(v[start:],axis=1).sum(),flush=True)
new=[f.copy()for f in mot]
for k,i in enumerate(I):new[i].update(contact=p[k].tolist(),normal=n[k].tolist(),contact_triangle=int(f[k]),incidence_deg=float(ang[k]))
Path('/workspace/C1_gorge_correction/TRAJET_LISSE_R3_FINAL.json').write_text(json.dumps({'motion':new,'max_angle_error_deg':float(max(abs(ang-55))),'new_max_turn_deg':float(turns(v)[start:].max()),'late_reversals':int(sum(turns(v)[start:]>90)),'max_displacement_mm':float(np.linalg.norm(Q-P,axis=1).max()),'optimizer_success':bool(res.success)},separators=(',',':')))
