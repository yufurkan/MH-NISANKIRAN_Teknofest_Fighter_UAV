#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <cv_bridge/cv_bridge.hpp>
#include <opencv2/opencv.hpp>
#include <opencv2/dnn.hpp>
#include <mutex>

using namespace std::chrono_literals;

class Targeter : public rclcpp::Node {
public:
    Targeter() : Node("targeter_node") {
        
        // ABONELİK AYARLARI 
        // Best Effort
        image_sub_ = this->create_subscription<sensor_msgs::msg::Image>("/world/default/model/rc_cessna_1/link/base_link/sensor/camera/image",rclcpp::SensorDataQoS(),std::bind(&Targeter::image_callback, this, std::placeholders::_1));

    
        std::string model_path = "/home/federstation/nisankiran_ws/best.onnx";net_ = cv::dnn::readNetFromONNX(model_path);    //model yolu

        // net_.setPreferableBackend(cv::dnn::DNN_BACKEND_CUDA);
        // net_.setPreferableTarget(cv::dnn::DNN_TARGET_CUDA);

        cv::namedWindow("Nisankiran HUD", cv::WINDOW_NORMAL);
        cv::resizeWindow("Nisankiran HUD", 1280, 720);

        // Yaklaşık 30 FPS
        display_timer_ = this->create_wall_timer(33ms, std::bind(&Targeter::display_callback, this));

        RCLCPP_INFO(this->get_logger(), "[VISION] Görsel nişangah sistemi aktif. Düşman aranıyor...");
    }

private:
    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr image_sub_;
    rclcpp::TimerBase::SharedPtr display_timer_;

    cv::dnn::Net net_;
    cv::Mat latest_frame_;
    std::mutex frame_mutex_; // Thread çakışmasını önlemek için kilit 

    int lock_frames_ = 0;
    const int REQUIRED_FRAMES_FOR_KILL = 120; // 4 saniyelik (30fps) kilitlenme süresi






    // --- KAMERA VERİSİ ALMA

    void image_callback(const sensor_msgs::msg::Image::SharedPtr msg) {
        try {

            auto cv_ptr = cv_bridge::toCvCopy(msg, "bgr8");
            cv::Mat frame = cv_ptr->image;

            cv::Mat processed = process_frame(frame);

  
            {
                std::lock_guard<std::mutex> lock(frame_mutex_);
                latest_frame_ = processed.clone();
            }

        } catch (const cv_bridge::Exception& e) {
            RCLCPP_ERROR(this->get_logger(), "[HATA] cv_bridge: %s", e.what());
        }
    }





    // kilitlenme
    cv::Mat process_frame(cv::Mat& frame) {
        int center_x = frame.cols / 2;
        int center_y = frame.rows / 2;

        // Görüntüyü YOLO'nun anlayacağı "blob" formatına çevir (640x640 resize)
        cv::Mat blob;
        cv::dnn::blobFromImage(frame, blob, 1.0/255.0, cv::Size(640, 640), cv::Scalar(0,0,0), true, false);
        net_.setInput(blob);

        std::vector<cv::Mat> outputs;
        try {
            net_.forward(outputs, std::vector<std::string>{"output0"});
        } catch (const cv::Exception& e) {
            RCLCPP_ERROR(this->get_logger(), "[VISION] Model ileri besleme hatası: %s", e.what());
            return frame;
        }

        bool enemy_detected = false;
        cv::Rect enemy_bbox;
        float max_conf = 0.0f;
        const float CONF_THRESHOLD = 0.5f;

        // YOLOv11 Tensor İşlemleri 
        if (!outputs.empty()) {
            cv::Mat out = outputs[0];
            if (out.dims == 3) {
                if (out.size[2] == 8400) { 
                    out = out.reshape(1, 84);
                    cv::transpose(out, out); 
                } else {
                    out = out.reshape(1, out.size[1]);
                }
            }


            // En güvenilir hedefi bul 
            for (int i = 0; i < out.rows; ++i) {
                float* row = out.ptr<float>(i);
                float confidence = row[4];

                if (confidence > CONF_THRESHOLD && confidence > max_conf) {
                    max_conf = confidence;

                    // Koordinatları orijinal frame boyutuna geri ölçekle
                    float x_scale = static_cast<float>(frame.cols) / 640.0f;
                    float y_scale = static_cast<float>(frame.rows) / 640.0f;

                    int left   = static_cast<int>((row[0] - 0.5f * row[2]) * x_scale);
                    int top    = static_cast<int>((row[1] - 0.5f * row[3]) * y_scale);
                    int width  = static_cast<int>(row[2] * x_scale);
                    int height = static_cast<int>(row[3] * y_scale);

                    enemy_bbox = cv::Rect(left, top, width, height);
                    enemy_detected = true;
                }
            }
        }

        cv::Mat out_img = frame.clone();    

        //TAKİP VE VURUŞ 
        if (enemy_detected) {
            int bbox_cx = enemy_bbox.x + enemy_bbox.width / 2;
            int bbox_cy = enemy_bbox.y + enemy_bbox.height / 2;
            
  
            int dist = static_cast<int>(std::hypot(bbox_cx - center_x, bbox_cy - center_y));


            bool in_crosshair = (dist < 100);
            bool in_range = (enemy_bbox.width > 80 && enemy_bbox.height > 80);

            if (in_crosshair && in_range) {
                lock_frames_++;
                if (lock_frames_ == REQUIRED_FRAMES_FOR_KILL) {
                    RCLCPP_INFO(this->get_logger(), "[HEDEF] Kilit tamamlandı. Atış onaylandı!");
                    lock_frames_ = 0; // Atış sonrası sıfırla
                } else if (lock_frames_ % 10 == 0) {
                    RCLCPP_INFO(this->get_logger(), "[HEDEF] Kilitleniliyor: %.1f / 4.0 Saniye...", lock_frames_ / 30.0f);
                }
            } else if (lock_frames_ > 0) {
                RCLCPP_WARN(this->get_logger(), "[SISTEM] Hedef nişangah dışına çıktı! Kilit kırıldı.");
                lock_frames_ = 0;
            }
            cv::rectangle(out_img, enemy_bbox, cv::Scalar(0, 0, 255), 3); // Kilit rengi KIRMIZI
        } else if (lock_frames_ > 0) {
            RCLCPP_WARN(this->get_logger(), "[SISTEM] Hedef görsel temas dışı!");
            lock_frames_ = 0;
        }

        // HUD Üzerine Nişangah Dairesi Çiz
        cv::circle(out_img, cv::Point(center_x, center_y), 100, cv::Scalar(0, 255, 0), 2);
        return out_img;
    }




    // HUD GÖSTERİM DÖNGÜSÜ
    void display_callback() {
        std::lock_guard<std::mutex> lock(frame_mutex_);
        if (!latest_frame_.empty()) {
            cv::imshow("Nisankiran HUD", latest_frame_);
            cv::waitKey(1); // Pencerenin donmaması için şart
        }
    }
};

int main(int argc, char * argv[]) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<Targeter>());
    rclcpp::shutdown();
    return 0;
}