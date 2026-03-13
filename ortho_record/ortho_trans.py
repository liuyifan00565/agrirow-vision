import cv2
import numpy as np
import math


class OrthoTransformer:
    def __init__(self):
        self.set_resolution(0.1)

    """
    设置相机内参：
    fov_x_deg：相机横向角度，单位为角度制
    fov_y_deg：相机纵向角度，单位为角度制
    K：标定算法求解的内参矩阵
    dist：标定算法求解的畸变系数
    """

    def set_internal_parameters(self, fov_x_deg, fov_y_deg,K, dist):
        """Set internal parameters for the camera."""
        self.fov_x = math.radians(fov_x_deg)
        self.fov_y = math.radians(fov_y_deg)
        self.K = K
        self.dist = dist

    """
    转换后图像的像素分辨率，表示1像素对应多少厘米
    """
    def set_resolution(self, resolution):
        """Set internal parameters for the camera."""
        self.resolution = resolution
        self.pixels_per_meter = 100 / self.resolution

    """
    设置相机拍摄的外参
    h：相机的安装高度，单位为米
    tilt_angle_deg：相机安装的俯仰角，单位为角度制。

    俯仰角的定义：0°为水平，90°为垂直向上拍摄，-90°为垂直向下拍摄

    """
    def set_external_parameters(self, h, tilt_angle_deg):
        """Set external parameters for the camera."""
        self.tilt_angle = math.radians(tilt_angle_deg)
        self.h = h

    """
    设置相机拍摄图像的原始分辨率，顺序为（高的像素，宽的像素）
    """
    def set_camera_img_shape(self, img_shape):
        self.camera_img_shape = img_shape

    """
    计算各种转换参数，包括：
    地面尺寸
    目标图像分辨率
    最终投影矩阵（单应性矩阵H）
    注意：
    当调用set_external_parameters()改变了外参，此函数也需要再次调用，重新计算各种转换参数
    """
    def calc_transfor_params(self):
        self.calculate_ground_dimensions()
        self.calculate_target_pixel_size()
        self.calc_Homography()
        self.adjust_homography()


    def calculate_ground_dimensions(self):
        """计算地面覆盖范围（考虑相机倾斜角）"""
        # qinxiejiao = 0 - self.tilt_angle   #math.radians(23)
        # self.h = self.h / math.cos(self.fov_y/2+qinxiejiao) * math.cos(self.fov_y/2)
        # self.W_ground =   2 * self.h * math.tan(self.fov_x/2)
        # self.H_ground =   2 * self.h * math.tan(self.fov_y/2) 

        self.h = self.h / math.cos(self.tilt_angle)
        self.W_ground = 2 * self.h * math.tan(self.fov_x/2) 
        self.H_ground = 2 * self.h * math.tan(self.fov_y/2) 

    def calculate_target_pixel_size(self):
        self.target_width = int(round(self.W_ground * self.pixels_per_meter))
        self.target_height = int(round(self.H_ground * self.pixels_per_meter))
        print("target_pixel_size = ",(self.target_width,self.target_height))

    def calc_Homography(self):

        R_x = np.array([
                [1, 0, 0],
                [0, math.cos(self.tilt_angle), -math.sin(self.tilt_angle)],
                [0, math.sin(self.tilt_angle), math.cos(self.tilt_angle)]
                ], dtype=np.float32)
        tvec = np.array([[0], [0], [self.h]], dtype=np.float32)

        H = self.K @ np.hstack((R_x[:, :2], tvec))

        self.H = H

        H_inv = np.linalg.inv(H)

        scale_M = np.diag([self.pixels_per_meter, self.pixels_per_meter, 1])
        H_scaled = scale_M @ H_inv

        self.H_scaled = H_scaled



    def adjust_homography(self):
        """根据目标输出尺寸，调整单应矩阵"""
        h, w = self.camera_img_shape[:2]
        corners = np.array([[0, 0], [w, 0], [0, h], [w, h]], dtype=np.float32)
        warped_corners = cv2.perspectiveTransform(corners.reshape(1, -1, 2), self.H_scaled).reshape(-1, 2)

        x_min, y_min = warped_corners.min(axis=0)
        x_max, y_max = warped_corners.max(axis=0)

        scale_x = self.target_width / (x_max - x_min)
        scale_y = self.target_height / (y_max - y_min)
        scale = min(scale_x, scale_y)

        adjust_M = np.array([
            [scale, 0, -x_min * scale],
            [0, scale, -y_min * scale],
            [0, 0, 1]
        ])

        final_H = adjust_M @ self.H_scaled
        self.final_H = final_H

    
    def eval(self,transformed_img):
        img = cv2.imread(transformed_img)
        print(img.shape)
        # 棋盘格设置
        pattern_size = (7,9)
        # square_size = 0.05  # 单位：米（5cm）
        found, corners = cv2.findChessboardCorners(img, pattern_size)


        # 验证棋盘格方格像素大小
        if found:
            # print(len(corners))
            # print(corners.shape)
            # # print(corners[0][0][0],corners[0][0][1])
            # # print(corners[1][0][0],corners[1][0][1])
            # for i in range(len(corners)):
            #     if i != 0 and i % 7  == 0:
            #         print("\n")
            #     print(corners[i][0][0],corners[i][0][1],',',end=' ')
            # pt1 = cv2.perspectiveTransform(corners[0].reshape(1, 1, 2), self.H)[0][0]
            # pt2 = cv2.perspectiveTransform(corners[1].reshape(1, 1, 2), self.H)[0][0]
            # square_pixels = np.linalg.norm(pt2 - pt1)
            # print(f"验证：鸟瞰图中每格边长 ≈ {square_pixels:.2f} 像素（应为10像素 = 5cm ÷ 0.5cm/pixel）")
            grid_w = corners[1][0][0]-corners[0][0][0]
            grid_h = corners[7][0][1]-corners[0][0][1]
            w_p_c = PixelCentimeter(self.resolution,5,grid_w)
            h_p_c = PixelCentimeter(self.resolution,5,grid_h)   
            print("长",w_p_c)
            print("宽",h_p_c)



    # imgfile = 'D:\\tmp\\1-130\\1.png'
    def transform(self,img):

        # 读取图像
        # img = cv2.imread(imgfile)
        # print('img.shape = ',img.shape)
        # 去畸变
        img_undist = cv2.undistort(img, self.K, self.dist)
        # print('img_undist=',img_undist.shape)

        result = cv2.warpPerspective(img_undist, self.final_H, (self.target_width,self.target_height), flags=cv2.INTER_LINEAR)
        # result = cv2.warpPerspective(img_undist, self.final_H, (self.target_width,self.target_height), flags=cv2.INTER_CUBIC)


        # cv2.imwrite(outputimg, result, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return result





class PixelCentimeter:
    def __init__(self, resolution, grid_width, pixel_num):
        self.resolution = resolution
        self.grid_width = grid_width
        self.pixel_num = pixel_num
    def get_golden_pixel_num(self):
        return 1 / self.resolution * self.grid_width
    
    def get_estimated_grid_width(self):
        return self.resolution * self.pixel_num
    
    def get_error(self):
        return abs((self.get_estimated_grid_width() - self.grid_width))/self.grid_width
    
    def __str__(self):
        return f"真实尺寸: {self.grid_width}, 理想像素: {self.get_golden_pixel_num():.2f}, 变换后像素: {self.pixel_num:.2f}, 估算尺寸: {self.get_estimated_grid_width():.2f}, 尺寸误差: {self.get_error():.2f}"
    


def create_ortho_trans(
        fov_x_deg,
        fov_y_deg,
        K,
        dist,
        camera_img_shape, # 设置相机拍摄图像的原始分辨率，顺序为（高的像素，宽的像素）
        resolution,
        h,
        tilt_angle_deg
        ):
    ortho = OrthoTransformer()
    ortho.set_internal_parameters(fov_x_deg,fov_y_deg,K,dist)
    ortho.set_camera_img_shape(camera_img_shape)
    ortho.set_resolution(resolution)

    ortho.set_external_parameters(h,tilt_angle_deg)  #当改变外参的时候，重新计算转换参数
    ortho.calc_transfor_params()
    return ortho
    



if  __name__ == '__main__':

    # K = np.array([[1122.52,0,430.99], [0,1656.21,294.12], [0,0,1]], dtype=np.float32)
    # dist = np.array([0.6327,-7.6199,-0.0714,0.0149,48.3834], dtype=np.float32)
    # fov_x_deg = 65
    # fov_y_deg = 46
    # h = 1.3
    # tilt_angle_deg = -49
    # resolution = 0.1
    # camera_img_shape = (605, 816)

    # K = np.array([[1.37132060e+03,0.00000000e+00,9.66102735e+02],
    #               [0.00000000e+00,1.36754059e+03,5.76855975e+02],
    #               [0.00000000e+00,0.00000000e+00,1.00000000e+00]], 
    #               dtype=np.float32)
    # dist = np.array([0.00772921,0.01609,-0.00052918,-0.00055093,-0.05750124], dtype=np.float32)

    K=np.array([[1.36074827e+03, 0.00000000e+00, 9.65363696e+02], 
                [0.00000000e+00, 1.35918014e+03, 5.86850945e+02], 
                [0,0,1]], dtype=np.float32)
    dist = np.array([0.00780561,  0.00221039, -0.00031791,  0.00078508, -0.03267454], dtype=np.float32)


    fov_x_deg = 65
    fov_y_deg = 46
    h = 1.3
    tilt_angle_deg = -23
    resolution = 0.1
    # camera_img_shape = (1080, 1920, 3)
    camera_img_shape = (599, 820, 3)




    ortho = OrthoTransformer()
    ortho.set_internal_parameters(fov_x_deg,fov_y_deg,K,dist)
    ortho.set_camera_img_shape(camera_img_shape)
    ortho.set_resolution(resolution)

    ortho.set_external_parameters(h,tilt_angle_deg)  #当改变外参的时候，重新计算转换参数
    ortho.calc_transfor_params()

    # imgfile = 'C:\\Users\\admin\\Desktop\\biaoding\\zonghe\\frame_56.jpg'
    # outputimg = 'D:\\tmp\\1-130\\56ab.jpg'
    imgfile = 'D:\\tmp\\1-130\\2.png'
    outputimg = 'D:\\tmp\\1-130\\2a.jpg'
    img_matrices = ortho.transform(imgfile)
    cv2.imwrite(outputimg, img_matrices, [cv2.IMWRITE_JPEG_QUALITY, 95])

    # ortho.eval('D:\\tmp\\1-130\\bird_eye_view_2.png')