"""CPU-only inference of our hash-verified, independently validated photo model."""
import base64
import hashlib
import io
import json
import os
import sys


class PhotoReader:
    def __init__(self):
        from .content_visual import DATA,model_contract
        contract=model_contract()
        if contract is None:raise ValueError('검증된 사진 모델이 없습니다.')
        import paddle
        self.paddle=paddle;paddle.set_device('cpu')
        model=paddle.vision.models.resnet18(pretrained=False)
        model.fc=paddle.nn.Sequential(paddle.nn.Dropout(contract.get('dropout',.25)),paddle.nn.Linear(512,3))
        # Only the locally approved file whose complete SHA was just verified is loaded.
        weights=paddle.load(str(DATA/'model.pdparams'))
        expected=model.state_dict()
        if set(weights)!=set(expected) or any(list(weights[k].shape)!=list(expected[k].shape) for k in expected):
            raise ValueError('사진 모델 구조 불일치')
        model.set_state_dict(weights);model.eval()
        self.model=model;self.contract=contract

    def read(self,data):
        import numpy as np
        from PIL import Image,ImageOps
        from .content_visual import TOPICS
        Image.MAX_IMAGE_PIXELS=8_000_000
        with Image.open(io.BytesIO(data)) as original:
            if original.width*original.height>8_000_000 or min(original.size)<8 or original.format not in ('PNG','JPEG','WEBP','GIF'):
                raise ValueError('지원하지 않는 사진 형식·크기')
            # Match training exactly, including alpha handling and aspect-preserving pad.
            image=original.convert('RGB')
            image=ImageOps.pad(image,(224,224),method=Image.Resampling.BILINEAR,color=(127,127,127))
        values=np.asarray(image,dtype='float32')/255.
        x=((values-np.array([.485,.456,.406],dtype='float32'))/np.array([.229,.224,.225],dtype='float32')).transpose(2,0,1)[None].copy()
        with self.paddle.no_grad():p=self.paddle.nn.functional.sigmoid(self.model(self.paddle.to_tensor(x))).numpy()[0]
        if p.shape!=(3,) or not np.isfinite(p).all():raise ValueError('사진 모델 출력 오류')
        return {'status':'completed','model':'ResNet18 · 이미지 분류','model_sha256':self.contract['sha256'],
                'image_sha256':hashlib.sha256(data).hexdigest(),'score_kind':'uncalibrated_model_score',
                'scores':{topic:float(p[k]) for k,topic in enumerate(TOPICS)},'thresholds':self.contract['thresholds']}


def main():
    protocol=os.fdopen(os.dup(sys.stdout.fileno()),'w',encoding='utf-8',buffering=1)
    os.dup2(sys.stderr.fileno(),sys.stdout.fileno());reader=None
    for line in sys.stdin:
        try:
            if len(line)>2_800_000:raise ValueError('사진 입력 크기 한도')
            data=base64.b64decode(json.loads(line)['image'],validate=True)
            if len(data)>2_000_000:raise ValueError('사진 크기 한도')
            if reader is None:reader=PhotoReader()
            result=reader.read(data)
        except Exception as error:result={'status':'failed','message':str(error)[:160]}
        protocol.write(json.dumps(result,ensure_ascii=True)+'\n')


if __name__=='__main__':main()
