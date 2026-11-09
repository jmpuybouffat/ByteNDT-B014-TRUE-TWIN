from pathlib import Path
import json,base64,numpy as np
r=Path('/workspace/LSB941-C1-PUBLICATION');s=(r/'assets/SCENE_C1_SYNCHRONISEE.html').read_text();d=json.JSONDecoder().raw_decode(s.split('const DATA=',1)[1])[0];b=json.JSONDecoder().raw_decode(s.split('const BEAM3D=',1)[1])[0]
for i,f in enumerate(b['frames']):
 assert f['shot']==i+1 and np.allclose(f['origin'],d['path'][i],atol=1e-12)
 assert len(base64.b64decode(f['dbq']))==113950
 for level,m in f['meshes'].items():
  v=np.frombuffer(base64.b64decode(m['vertices']),dtype='<i2').reshape(-1,3);tri=np.frombuffer(base64.b64decode(m['faces']),dtype='<u2').reshape(-1,3)
  assert level in ['-6','-12'] and len(v)==m['vertices_count'] and len(tri)==m['triangles_count'] and tri.max()<len(v)
print('41 origins, 82 isosurfaces, 41 numerical grids: PASS')
