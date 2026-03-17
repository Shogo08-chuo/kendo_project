import boto3

model_arn = "arn:aws:rekognition:ap-northeast-1:625966732318:project/kendo-waza-detection/version/kendo-waza-detection.2026-01-28T14.21.35/1769577694890"

def analyze_kendo_waza(photo_path):
    client = boto3.client('rekognition', region_name='ap-northeast-1')

    with open(photo_path, 'rb') as image:
        response = client.detect_custom_labels(
            ProjectVersionArn=model_arn,
            Image={'Bytes': image.read()},
            MinConfidence=1
        )

    labels = response['CustomLabels']
    
    print(f"--- 判定結果 (ベスト回答) ---")
    if not labels:
        print("技は検出されませんでした。")
    else:
        best_label = max(labels, key=lambda x: x['Confidence'])
        
        name = best_label['Name']
        confidence = best_label['Confidence']
        
        print(f"AIの推論結果: {name} (自信度: {confidence:.2f}%)")

analyze_kendo_waza("test_image.jpg")