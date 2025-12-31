import cv2

# Videonuzun tam dosya yolunu buraya yazın
video_yolu = '/home/ismail/Downloads/kayit_1dk.mp4' 

# Videoyu yakalamak için bir VideoCapture nesnesi oluşturun
cap = cv2.VideoCapture(video_yolu)

# Videonun başarıyla açılıp açılmadığını kontrol edin
if not cap.isOpened():
    print(f"Hata: Video dosyası açılamadı! Yolun doğru olduğundan emin olun: {video_yolu}")
else:
    # Video açık olduğu sürece döngüyü sürdürün
    while cap.isOpened():
        # Videodan bir sonraki kareyi okuyun
        # ret: karenin başarıyla okunup okunmadığını belirten bir boolean (True/False)
        # frame: okunan video karesi (bir NumPy dizisi)
        ret, frame = cap.read()

        # Eğer kare başarıyla okunduysa (ret == True)
        if ret:
            # Kareyi bir pencerede gösterin
            cv2.imshow('Video Oynatıcı', frame)

            # 'q' tuşuna basılırsa döngüden çık
            if cv2.waitKey(25) & 0xFF == ord('q'):
                break
        # Video bitti veya okuma hatası oluştu
        else:
            break

# Her şey bittiğinde, video yakalama nesnesini serbest bırakın
cap.release()

# Tüm OpenCV pencerelerini kapatın
cv2.destroyAllWindows()

print("Video oynatma tamamlandı.")