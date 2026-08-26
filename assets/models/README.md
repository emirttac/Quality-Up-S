# Super-resolution weights

## Required (bundled)
- `FSRCNN_x2.pb`
- `FSRCNN_x4.pb`

## Optional — Real-ESRGAN (high quality)
Place ONNX exports here to enable the Real-ESRGAN model in the UI:

- `realesrgan-x2.onnx`
- `realesrgan-x4.onnx`

Compatible exports typically use NCHW RGB float32 input/output in `[0, 1]`.
You can convert official Real-ESRGAN PyTorch weights with tools such as
`torch.onnx.export`, or download community ONNX builds that match this layout.

Without these files the app still runs on FSRCNN; selecting Real-ESRGAN will
prompt you to add the weights.
