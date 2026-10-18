import trimesh,numpy as np,glob,os,itertools,sys
B=sys.argv[1]; F=sys.argv[2]
P={'Parte_2_1_Vasil':trimesh.load(F),'acople':trimesh.load(B+'/acople_punta_vasil_x1.5.stl'),'contraplaca':trimesh.load(B+'/contraplaca_acople_x1.5.stl')}
for f in sorted(glob.glob(B+'/ASM_*.stl')): P[os.path.basename(f)[4:-4]]=trimesh.load(f)
bad=0
for a,b in itertools.combinations(P,2):
    if not (np.all(P[a].bounds[0]<P[b].bounds[1]) and np.all(P[b].bounds[0]<P[a].bounds[1])): continue
    i=trimesh.boolean.intersection([P[a],P[b]],engine='manifold'); v=abs(i.volume) if len(i.faces) else 0
    if v>0.5: print(f'COLISIÓN {a} x {b}: {v:.1f} mm3'); bad+=1
from trimesh.proximity import closest_point
for a,b in [('acople','Parte_2_1_Vasil'),('contraplaca','Parte_2_1_Vasil'),('acople','base_plate'),('acople','contraplaca')]:
    _,d,_=closest_point(P[b],P[a].sample(20000)); print(f'distancia mínima {a} - {b}: {d.min():.2f} mm')
print('colisiones:',bad)
