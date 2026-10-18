import trimesh,numpy as np,json,sys,glob,os
B=sys.argv[1]
gm=json.load(open(B+'/gripper_meta.json')); sx,sz=gm['servo_slot_center_xz']
def bx(x0,x1,y0,y1,z0,z1):
    b=trimesh.creation.box(extents=[x1-x0,y1-y0,z1-z0]); b.apply_translation([(x0+x1)/2,(y0+y1)/2,(z0+z1)/2]); return b
# MG90S aprox.: cuerpo 12.2 x 22.8, orejetas 32 x 12.2 x 2.5 bajo la placa, parte superior hasta +4.5 dentro del hueco
body=bx(sx-6.1,sx+6.1,-18.5,4.5,sz-11.4,sz+11.4)
ears=bx(sx-6.1,sx+6.1,-2.5,0,sz-16,sz+16)
servo=trimesh.boolean.union([body,ears],engine='manifold'); servo.export(B+'/servo_MG90S_aprox_x1.stl')
P={os.path.basename(f)[:-4]:trimesh.load(f) for f in glob.glob(B+'/*_x1.5.stl') if 'muneca' not in f}
for k,m in P.items():
    i=trimesh.boolean.intersection([servo,m],engine='manifold'); v=abs(i.volume) if len(i.faces) else 0
    if v>0.1: print('servo x',k,round(v,2))
# margen en el hueco
print('hueco 12.6x23.2 vs cuerpo 12.2x22.8 -> 0.2 mm por lado')
