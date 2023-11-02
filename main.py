import json
import uuid
import time
from threading import Thread

from flask import Flask, request, send_file, jsonify, send_from_directory

import argparse
import cv2
import glob
import numpy as np
import os
import torch
from basicsr.utils import imwrite
from mpmath import ln

from gfpgan import GFPGANer

ALLOWED_EXTENSIONS = {'png', 'jpg', 'JPG', 'jpeg', 'PNG', 'bmp'}


def printLog(logInfo):
    print(f'{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())} -- log : {logInfo}')
    # 写入log.txt
    with open('log.txt', 'a') as f:
        f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())} -- log : {logInfo}\n')
    return


# 判断文件结尾是否为允许的文件类型
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def process_image(random_str, file_name, data):
    base_img_path = 'img/' + random_str + '/input'
    out_put_path = 'img/' + random_str + '/output'

    bg_upsampler = 'realesrgan'
    version = '1.3'
    upscale = 2
    aligned = None
    only_center_face = False
    weight = 0.5
    suffix = None
    ext = 'auto'

    # if 'bg_upsampler' in data:
    #     bg_upsampler = data['bg_upsampler']
    if 'version' in data:
        version = data['version']
    if 'upscale' in data:
        upscale = int(data['upscale'])
    if 'aligned' in data:
        aligned = data['aligned']
    if 'only_center_face' in data:
        only_center_face = data['only_center_face']
    if 'weight' in data:
        weight = data['weight']
    if 'suffix' in data:
        suffix = data['suffix']
    if 'ext' in data:
        ext = data['ext']

    # ------------------------ 输入 & 输出 ------------------------
    if base_img_path.endswith('/'):
        base_img_path = base_img_path[:-1]
    if os.path.isfile(base_img_path):
        img_list = [base_img_path]
    else:
        img_list = sorted(glob.glob(os.path.join(base_img_path, '*')))

    os.makedirs(out_put_path, exist_ok=True)

    # ------------------------ set up background upsampler ------------------------
    if bg_upsampler == 'realesrgan':
        if not torch.cuda.is_available():  # CPU
            bg_upsampler = None
        else:
            from basicsr.archs.rrdbnet_arch import RRDBNet
            from realesrgan import RealESRGANer
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
            bg_upsampler = RealESRGANer(
                scale=2,
                model_path='https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth',
                model=model,
                tile=True,
                tile_pad=10,
                pre_pad=0,
                half=True)  # CPU模式需要设置为False
    else:
        bg_upsampler = None

    # ------------------------ set up Aimage restorer ------------------------
    if version == '1':
        arch = 'original'
        channel_multiplier = 1
        model_name = 'GFPGANv1'
        url = 'https://github.com/TencentARC/GFPGAN/releases/download/v0.1.0/GFPGANv1.pth'
    elif version == '1.2':
        arch = 'clean'
        channel_multiplier = 2
        model_name = 'GFPGANCleanv1-NoCE-C2'
        url = 'https://github.com/TencentARC/GFPGAN/releases/download/v0.2.0/GFPGANCleanv1-NoCE-C2.pth'
    elif version == '1.3':
        arch = 'clean'
        channel_multiplier = 2
        model_name = 'GFPGANv1.3'
        url = 'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.3.pth'
    elif version == '1.4':
        arch = 'clean'
        channel_multiplier = 2
        model_name = 'GFPGANv1.4'
        url = 'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth'
    elif version == 'RestoreFormer':
        arch = 'RestoreFormer'
        channel_multiplier = 2
        model_name = 'RestoreFormer'
        url = 'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/RestoreFormer.pth'
    else:
        raise ValueError(f'模型版本选择错误 {version}.')

    # 确定模型路径
    model_path = os.path.join('experiments/pretrained_models', model_name + '.pth')
    if not os.path.isfile(model_path):
        model_path = os.path.join('gfpgan/weights', model_name + '.pth')
    if not os.path.isfile(model_path):
        # 从url下载预训练模型
        model_path = url

    restorer = GFPGANer(
        model_path=model_path,
        upscale=upscale,
        arch=arch,
        channel_multiplier=channel_multiplier,
        bg_upsampler=bg_upsampler)

    # ------------------------ 修复 ------------------------
    for img_path in img_list:
        # 读取照片
        img_name = os.path.basename(img_path)
        printLog(f'开始使用模型 {version} 处理图片： {img_name} ...')
        basename, ext = os.path.splitext(img_name)
        input_img = cv2.imread(img_path, cv2.IMREAD_COLOR)

        # 如果需要，恢复人脸和背景
        cropped_faces, restored_faces, restored_img = restorer.enhance(
            input_img,
            has_aligned=aligned,
            only_center_face=only_center_face,
            paste_back=True,
            weight=weight)

        # 保存人脸
        for idx, (cropped_face, restored_face) in enumerate(zip(cropped_faces, restored_faces)):
            # 保存拷贝下来的人脸
            save_crop_path = os.path.join(out_put_path, 'cropped_faces', f'{basename}_{idx:02d}.png')
            imwrite(cropped_face, save_crop_path)
            # 保存修复后的人脸
            if suffix is not None:
                save_face_name = f'{basename}_{idx:02d}_{suffix}.png'
            else:
                save_face_name = f'{basename}_{idx:02d}.png'
            save_restore_path = os.path.join(out_put_path, 'restored_faces', save_face_name)
            imwrite(restored_face, save_restore_path)
            # 保存比较图片
            cmp_img = np.concatenate((cropped_face, restored_face), axis=1)
            imwrite(cmp_img, os.path.join(out_put_path, 'cmp', f'{basename}_{idx:02d}.png'))

        # 保存修复后的图片
        if restored_img is not None:
            if ext == 'auto':
                extension = ext[1:]
            else:
                extension = ext
            if suffix is not None:
                save_restore_path = os.path.join(out_put_path, f'{basename}_{suffix}{extension}')
            else:
                save_restore_path = os.path.join(out_put_path, f'{basename}{extension}')
            imwrite(restored_img, save_restore_path)
        printLog(f'处理图片 {img_name} 完成')
    # 获取文件大小
    file_size = os.path.getsize('img/' + random_str + '/input/' + file_name)
    # 将处理时间写入time.txt后面
    with open('time.txt', 'a') as f:
        f.write(file_name + '\t\t\t' + data['upscale'] + '\t\t\t' + str(file_size) + '\t\t\t' + str(
            int(time.time()) - int(random_str[-10:])) + 's\n')
    os.makedirs('img/' + random_str + '/fin')


# 创建Flask应用
app = Flask(__name__)


@app.route('/')
def index():
    # 返回html文件
    return send_file('assets/index.html')


@app.route('/<path:path>')
def serve_assets(path):
    try:
        return send_from_directory('assets', path)
    except FileNotFoundError:
        return "文件不存在", 404


@app.route('/upload', methods=['POST'])
def upload_file():
    # 判断是否有文件上传
    if 'file' not in request.files:
        return "没有文件上传，请选择文件！", 400
    # 获取上传的文件
    file = request.files['file']

    # 判断文件是否为空
    if file.filename == '':
        return "文件为空，请重新选择文件！", 400

    # 判断文件是否为图片
    if not allowed_file(file.filename):
        return "文件类型不支持，请重新选择文件！", 400

    # 获取用户选择的参数
    data = request.form

    # 参数检查
    if 'upscale' in data:
        if data['upscale'] not in ['2', '4']:
            return "参数错误，请重新选择参数！", 400
    if 'version' in data:
        if data['version'] not in ['1.0', '1.1', '1.2', '1.3', '1.4', 'RestoreFormer']:
            return "参数错误，请重新选择参数！", 400

    # 生成随机数后面是时间戳
    random_str = str(uuid.uuid4()) + '-' + str(int(time.time()))

    # 判断文件夹是否存在
    while os.path.exists('img/' + random_str):
        random_str = str(uuid.uuid4())

    # 保存文件到服务器
    os.makedirs('img/' + random_str + '/input')
    file.save(os.path.join('img/' + random_str + '/input', file.filename))

    printLog('接收到图片：' + file.filename + '  random_str:' + random_str)

    # 开始处理图片
    t = Thread(target=process_image, args=(random_str, file.filename, data))
    t.start()

    # 返回随机数，便于获取文件
    return random_str


@app.route('/query', methods=['GET'])
def query():
    random_str = request.args.get('random_str')

    if not os.path.exists('img/' + random_str):
        # 设置返回状态码
        return '项目不存在，请重新选择！', 404

    # 根据时间戳判断是否超时
    judgeTime = int(time.time()) - int(random_str[-10:])

    if judgeTime > 1800:
        return '项目已过期，请重新上传！', 404

    # 查询是否处理完成
    if os.path.exists('img/' + random_str + '/fin'):  # 如果处理完成
        return jsonify(success=True)
    else:
        return jsonify(success=False)


@app.route('/download', methods=['GET'])
def download_file():
    random_str = request.args.get('random_str')
    type = request.args.get('type')
    fileName = request.args.get('filename')
    if not os.path.exists('img/' + random_str):
        # 设置返回状态码
        return '项目不存在，请重新选择！', 404

    # 根据时间戳判断是否超时
    if int(time.time()) - int(random_str[-10:]) > 1800:
        return '项目已过期，请重新上传！', 404

    # 判断文件夹是否存在
    if not os.path.exists('img/' + random_str + '/fin'):
        return '暂未完成处理，请等待处理完成后再试！', 404

    # 从服务器获取文件
    path = os.path.join('img/' + random_str + '/' + type, fileName)

    printLog('用户下载文件：' + path)

    # 下载文件
    return send_file(path, as_attachment=True)


@app.route('/tongji', methods=['GET'])
def tongji():
    # 查询文件夹下的文件夹数量
    return jsonify(len(os.listdir('img')))


@app.route('/gettime', methods=['GET'])
def gettime():
    random_str = request.args.get('random_str')
    file_name = request.args.get('file_name')

    # 获取文件大小
    file_size = os.path.getsize('img/' + random_str + '/input/' + file_name)
    second = 11.755 * ln(float(file_size)) - 118.56

    return jsonify(seconds=int(second))


# 主函数
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
    # app.run(host='0.0.0.0', port=443, ssl_context=('/root/.acme.sh/aimage.zhuanjie.ltd_ecc/fullchain.cer', '/root/.acme.sh/aimage.zhuanjie.ltd_ecc/aimage.zhuanjie.ltd.key'))
