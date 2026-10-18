import trimesh,numpy as np,sys
B=sys.argv[1]; L=lambda n: trimesh.load(f'{B}/{n}_x1.5.stl')
P={n:L(n) for n in ['base_plate','gear_left','gear_right','arm_left','arm_right','jaw_left','jaw_right']}
GL=np.array([44.43,-44.64]); GR=np.array([44.43,-11.64]); AL=np.array([14.43,-34.89]); AR=np.array([14.43,-21.39])
def rotY(m,c,ang):  # rotación en el plano XZ alrededor de (c) eje Y
    T=trimesh.transformations.rotation_matrix(ang,[0,1,0],[c[0],0,c[1]]); m=m.copy(); m.apply_transform(T); return m
def pose(phi):
    q={'base_plate':P['base_plate']}
    q['gear_left']=rotY(P['gear_left'],GL,phi); q['gear_right']=rotY(P['gear_right'],GR,-phi)
    q['arm_left']=rotY(P['arm_left'],AL,phi);  q['arm_right']=rotY(P['arm_right'],AR,-phi)
    for j,c,s in [('jaw_left',GL,phi),('jaw_right',GR,-phi)]:
        T=trimesh.transformations.rotation_matrix(s,[0,1,0],[c[0],0,c[1]])
        p0=np.array([-0.57,0,c[1]]); p1=trimesh.transformations.transform_points([p0],T)[0]
        m=P[j].copy(); m.apply_translation(p1-p0); q[j]=m
    return q
# sentido de apertura: el que separa las mordazas
for sgn in [1,-1]:
    q=pose(sgn*np.radians(10)); g=q['jaw_right'].bounds[0][2]-q['jaw_left'].bounds[1][2]
    print('signo',sgn,'hueco a 10°: %.1f'%g)
import itertools
def gap(q):
    # hueco real entre caras de agarre: distancia mínima entre las dos mordazas
    a=q['jaw_left'].sample(4000); _,d,_=trimesh.proximity.closest_point(q['jaw_right'],a); return d.min()
names=list(P)
for deg in [0,15,30,45,60,75,90]:
    q=pose(-np.radians(deg)); hits=[]
    for a,b in itertools.combinations(names,2):
        i=trimesh.boolean.intersection([q[a],q[b]],engine='manifold')
        v=abs(i.volume) if len(i.faces) else 0
        if v>1: hits.append(f'{a}x{b}:{v:.0f}')
    print(f'{deg:3d}°  hueco mordazas {gap(q):5.1f} mm  colisiones: {hits if hits else "ninguna"}')
