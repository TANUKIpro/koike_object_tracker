from transformers import Sam2VideoModel, Sam2VideoProcessor

m = Sam2VideoModel.from_pretrained("facebook/sam2.1-hiera-tiny")
p = Sam2VideoProcessor.from_pretrained("facebook/sam2.1-hiera-tiny")

print("ready")

