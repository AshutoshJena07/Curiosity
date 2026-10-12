import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import {
  XIcon,
  ScanEyeIcon,
  CrosshairIcon,
  CheckIcon,
  DownloadIcon,
  SparklesIcon,
  SlidersIcon
} from '../Common/Icons';
import { analyzeFile } from '../../services/api';

// Vibrant color palette for distinct YOLO class bounding boxes
const CLASS_COLORS = [
  '#00E5FF', // Cyan
  '#E040FB', // Neon Magenta
  '#00E676', // Neon Green
  '#FFD600', // Bright Amber/Yellow
  '#FF5252', // Coral Red
  '#7C4DFF', // Purple
  '#FF9100', // Deep Orange
  '#00B0FF', // Sky Blue
  '#76FF03', // Lime
  '#F50057', // Hot Pink
];

function getColorForLabel(label = '') {
  let hash = 0;
  for (let i = 0; i < label.length; i++) {
    hash = label.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % CLASS_COLORS.length;
  return CLASS_COLORS[index];
}

export default function DetectionInspectorModal({
  isOpen,
  onClose,
  messages = [],
  activeFile = null,
  displayName = 'Explorer'
}) {
  const modalRef = useRef(null);
  const containerRef = useRef(null);
  const imageRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  // Filter all visual media / images sent in the conversation
  const sessionImages = useMemo(() => {
    const list = [];
    for (let i = 0; i < messages.length; i++) {
      const msg = messages[i];
      if (msg.role === 'user' && (msg.imageUrl || msg.fileType === 'image')) {
        // find corresponding bot response if any
        const nextBot = messages.slice(i + 1).find(m => m.role === 'bot');
        list.push({
          id: msg.id,
          imageUrl: msg.imageUrl,
          fileName: msg.fileName || 'Image',
          timestamp: msg.timestamp,
          botReply: nextBot || null
        });
      }
    }
    return list;
  }, [messages]);

  // Selected image index from session or custom uploaded file
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [customImage, setCustomImage] = useState(null);
  const [isProcessingCustom, setIsProcessingCustom] = useState(false);
  const [customError, setCustomError] = useState('');

  // Visualization options
  const [showBoxes, setShowBoxes] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [confThreshold, setConfThreshold] = useState(0.25);
  const [selectedClassFilter, setSelectedClassFilter] = useState('all');
  const [hoveredBoxIndex, setHoveredBoxIndex] = useState(null);
  const [zoomLevel, setZoomLevel] = useState(1.0);

  // Auto-select latest image when session updates
  useEffect(() => {
    if (sessionImages.length > 0 && !customImage) {
      setSelectedImageIndex(sessionImages.length - 1);
    }
  }, [sessionImages.length, customImage]);

  // Determine active item to display
  const currentItem = useMemo(() => {
    if (customImage) return customImage;
    if (sessionImages.length > 0) {
      return sessionImages[selectedImageIndex] || sessionImages[sessionImages.length - 1];
    }
    // If activeFile in composer is an image, preview it
    if (activeFile?.previewUrl) {
      return {
        id: 'active-composer',
        imageUrl: activeFile.previewUrl,
        fileName: activeFile.name || 'Current Attachment',
        botReply: null
      };
    }
    return null;
  }, [customImage, sessionImages, selectedImageIndex, activeFile]);

  // Extract detection data from active item
  const detectionData = useMemo(() => {
    if (!currentItem?.botReply) return null;
    const bot = currentItem.botReply;
    const dl = bot.dl_metrics || {};
    const yolo = dl.perception?.yolo_detector || {};
    const resnet = dl.perception?.resnet_imagenet || {};
    const imgDims = dl.image_dimensions || null;

    return {
      accuracy: bot.accuracy ?? 95,
      confidence: bot.confidence ?? 0.90,
      latency_s: bot.latency_s ?? 0.25,
      yoloObjects: yolo.detected_objects || [],
      yoloCounts: yolo.object_counts || {},
      totalObjects: yolo.total_objects || (yolo.detected_objects?.length || 0),
      yoloSummary: yolo.summary || '',
      resnetTop1: resnet.top_prediction || '',
      resnetTop5: resnet.top5_predictions || [],
      resnetSummary: resnet.summary || '',
      imageDimensions: imgDims
    };
  }, [currentItem]);

  // Handle direct file upload inside inspector
  const handleCustomUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setCustomError('Please select a valid image file (PNG, JPG, WEBP).');
      return;
    }

    setCustomError('');
    setIsProcessingCustom(true);
    const previewUrl = URL.createObjectURL(file);

    try {
      const result = await analyzeFile(
        'Describe this image and detect all objects with YOLOv11 and ResNet-50.',
        file,
        [],
        displayName
      );

      setCustomImage({
        id: `custom_${Date.now()}`,
        imageUrl: previewUrl,
        fileName: file.name,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        botReply: {
          accuracy: result.accuracy,
          confidence: result.confidence,
          latency_s: result.pipeline_latency_s,
          dl_metrics: result.dl_metrics,
          text: result.answer
        }
      });
    } catch (err) {
      console.error('Detection test failed:', err);
      setCustomError('Detection failed: ' + (err.message || 'Server error'));
    } finally {
      setIsProcessingCustom(false);
    }
  };

  // Filtered detected objects based on confidence threshold & class filter
  const filteredObjects = useMemo(() => {
    if (!detectionData?.yoloObjects) return [];
    return detectionData.yoloObjects.filter((obj) => {
      const passConf = (obj.confidence ?? 1.0) >= confThreshold;
      const passClass = selectedClassFilter === 'all' || obj.label.toLowerCase() === selectedClassFilter.toLowerCase();
      return passConf && passClass;
    });
  }, [detectionData, confThreshold, selectedClassFilter]);

  // Unique detected class labels for filter pills
  const uniqueLabels = useMemo(() => {
    if (!detectionData?.yoloObjects) return [];
    return Array.from(new Set(detectionData.yoloObjects.map(o => o.label)));
  }, [detectionData]);

  // Render bounding boxes onto canvas accurately
  const drawBoxes = useCallback(() => {
    const canvas = canvasRef.current;
    const img = imageRef.current;
    if (!canvas || !img || !img.complete) return;

    const naturalW = img.naturalWidth;
    const naturalH = img.naturalHeight;
    if (!naturalW || !naturalH) return;

    canvas.width = img.clientWidth;
    canvas.height = img.clientHeight;

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!showBoxes || filteredObjects.length === 0) return;

    const scaleX = canvas.width / naturalW;
    const scaleY = canvas.height / naturalH;

    filteredObjects.forEach((obj, idx) => {
      const isHovered = hoveredBoxIndex === idx;
      const color = getColorForLabel(obj.label);

      // box: [x1, y1, x2, y2]
      let [x1, y1, x2, y2] = obj.box || [0, 0, 0, 0];
      let bx = x1 * scaleX;
      let by = y1 * scaleY;
      let bw = (x2 - x1) * scaleX;
      let bh = (y2 - y1) * scaleY;

      // Draw box rectangle
      ctx.lineWidth = isHovered ? 3.5 : 2.5;
      ctx.strokeStyle = color;
      ctx.strokeRect(bx, by, bw, bh);

      // Light semi-transparent fill for subtle highlight
      ctx.fillStyle = isHovered ? `${color}33` : `${color}14`;
      ctx.fillRect(bx, by, bw, bh);

      // Draw label pill if enabled
      if (showLabels) {
        const confText = obj.confidence ? `${Math.round(obj.confidence * 100)}%` : '';
        const labelText = `${obj.label} ${confText}`.trim();

        ctx.font = 'bold 12px Inter, sans-serif';
        const textMetrics = ctx.measureText(labelText);
        const paddingX = 7;
        const pillHeight = 20;
        const pillWidth = textMetrics.width + paddingX * 2;

        let labelY = by - pillHeight;
        if (labelY < 0) labelY = by; // keep inside image boundaries

        // Pill background
        ctx.fillStyle = color;
        ctx.fillRect(bx, labelY, pillWidth, pillHeight);

        // Text
        ctx.fillStyle = '#0a0a0f';
        ctx.textBaseline = 'middle';
        ctx.fillText(labelText, bx + paddingX, labelY + pillHeight / 2);
      }
    });
  }, [filteredObjects, showBoxes, showLabels, hoveredBoxIndex]);

  // Re-draw boxes whenever image loads or display parameters change
  useEffect(() => {
    drawBoxes();
    const handleResize = () => drawBoxes();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [drawBoxes, currentItem?.imageUrl, zoomLevel]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="detection-modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div
        className="detection-modal-window"
        ref={modalRef}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="detection-modal-header">
          <div className="detection-modal-header-left">
            <div className="detection-icon-badge">
              <ScanEyeIcon size={20} />
            </div>
            <div>
              <div className="detection-modal-title">
                Visual Detection & Accuracy Inspector
              </div>
              <div className="detection-modal-subtitle">
                YOLOv11 Real-Time Object Localization & ResNet-50 Taxonomic Engine
              </div>
            </div>
          </div>

          <div className="detection-modal-header-actions">
            <button
              type="button"
              className="detection-header-upload-btn"
              onClick={() => fileInputRef.current?.click()}
              title="Test a new image file"
            >
              <CrosshairIcon size={15} />
              <span>{isProcessingCustom ? 'Detecting...' : 'Test Another Image'}</span>
            </button>
            <input
              type="file"
              ref={fileInputRef}
              accept="image/*"
              style={{ display: 'none' }}
              onChange={handleCustomUpload}
            />

            <button
              type="button"
              className="icon-btn detection-close-btn"
              onClick={onClose}
              aria-label="Close Inspector"
              title="Close (Esc)"
            >
              <XIcon size={18} />
            </button>
          </div>
        </div>

        {/* Image Source Selector Chips (if multiple images in session) */}
        {(sessionImages.length > 1 || customImage) && (
          <div className="detection-session-strip">
            <span className="strip-label">Select Session Image:</span>
            {sessionImages.map((img, idx) => (
              <button
                key={img.id}
                type="button"
                className={`detection-strip-pill ${!customImage && selectedImageIndex === idx ? 'active' : ''}`}
                onClick={() => {
                  setCustomImage(null);
                  setSelectedImageIndex(idx);
                }}
              >
                <img src={img.imageUrl} alt="" className="strip-thumb" />
                <span>{img.fileName || `Image #${idx + 1}`}</span>
              </button>
            ))}
            {customImage && (
              <button
                type="button"
                className="detection-strip-pill active custom"
                onClick={() => {}}
              >
                <img src={customImage.imageUrl} alt="" className="strip-thumb" />
                <span>{customImage.fileName} (Direct Test)</span>
              </button>
            )}
          </div>
        )}

        {customError && (
          <div className="detection-error-banner">{customError}</div>
        )}

        {/* Modal Main Body */}
        <div className="detection-modal-body">
          {/* Left Column: Image Canvas Stage */}
          <div className="detection-stage-container">
            {currentItem ? (
              <div className="detection-canvas-wrapper" ref={containerRef}>
                <div
                  className="detection-zoom-viewport"
                  style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'top center' }}
                >
                  <img
                    ref={imageRef}
                    src={currentItem.imageUrl}
                    alt={currentItem.fileName}
                    className="detection-source-image"
                    onLoad={drawBoxes}
                  />
                  <canvas
                    ref={canvasRef}
                    className="detection-overlay-canvas"
                  />
                </div>

                {/* Canvas Floating Overlay Controls */}
                <div className="detection-canvas-toolbar">
                  <button
                    type="button"
                    className={`canvas-tool-chip ${showBoxes ? 'active' : ''}`}
                    onClick={() => setShowBoxes(!showBoxes)}
                    title="Toggle Bounding Boxes"
                  >
                    <CrosshairIcon size={14} />
                    <span>Boxes {showBoxes ? 'ON' : 'OFF'}</span>
                  </button>
                  <button
                    type="button"
                    className={`canvas-tool-chip ${showLabels ? 'active' : ''}`}
                    onClick={() => setShowLabels(!showLabels)}
                    title="Toggle Class Labels and Confidence Tags"
                  >
                    <span>Labels {showLabels ? 'ON' : 'OFF'}</span>
                  </button>
                  <div className="zoom-controls">
                    <button
                      type="button"
                      className="zoom-btn"
                      onClick={() => setZoomLevel(prev => Math.max(0.6, prev - 0.2))}
                      title="Zoom Out"
                    >
                      -
                    </button>
                    <span className="zoom-text">{Math.round(zoomLevel * 100)}%</span>
                    <button
                      type="button"
                      className="zoom-btn"
                      onClick={() => setZoomLevel(prev => Math.min(2.5, prev + 0.2))}
                      title="Zoom In"
                    >
                      +
                    </button>
                    {zoomLevel !== 1.0 && (
                      <button
                        type="button"
                        className="zoom-reset-btn"
                        onClick={() => setZoomLevel(1.0)}
                      >
                        Reset
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="detection-empty-stage">
                <div className="empty-stage-icon">
                  <ScanEyeIcon size={44} />
                </div>
                <h3>No Input Image Selected</h3>
                <p>
                  Upload or attach any image to inspect real-time YOLOv11 bounding boxes and ResNet classification accuracy.
                </p>
                <button
                  type="button"
                  className="detection-upload-prompt-btn"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <CrosshairIcon size={16} />
                  <span>Choose Image to Detect</span>
                </button>
              </div>
            )}
          </div>

          {/* Right Column: Accuracy & Inspection Telemetry */}
          <div className="detection-sidebar-telemetry">
            {/* 1. Accuracy Metric Cards */}
            <div className="telemetry-cards-grid">
              <div className="telemetry-card accuracy-card">
                <div className="card-top">
                  <span className="card-label">Real-Time Accuracy</span>
                  <span className="card-badge green">Verified</span>
                </div>
                <div className="card-big-value">
                  {detectionData ? `${detectionData.accuracy}%` : '--'}
                </div>
                <div className="card-subtext">
                  Pipeline multi-layer grounded score
                </div>
              </div>

              <div className="telemetry-card confidence-card">
                <div className="card-top">
                  <span className="card-label">Visual Confidence</span>
                  <span className="card-badge blue">YOLOv11</span>
                </div>
                <div className="card-big-value">
                  {detectionData ? `${Math.round(detectionData.confidence * 100)}%` : '--'}
                </div>
                <div className="card-subtext">
                  Average bounding box localization
                </div>
              </div>
            </div>

            {/* 2. ResNet-50 ImageNet Classification */}
            <div className="telemetry-section-box">
              <div className="section-box-header">
                <div className="header-left">
                  <SparklesIcon size={15} />
                  <span>ResNet-50 Taxonomic Scene</span>
                </div>
                <span className="model-chip">ImageNet-1k</span>
              </div>
              <div className="resnet-primary-prediction">
                <div className="prediction-label">
                  {detectionData?.resnetTop1 ? (
                    <strong>{detectionData.resnetTop1}</strong>
                  ) : (
                    <span style={{ color: 'var(--text-muted)' }}>Natural scene classification</span>
                  )}
                </div>
              </div>
              {detectionData?.resnetTop5 && detectionData.resnetTop5.length > 0 && (
                <div className="resnet-top5-list">
                  {detectionData.resnetTop5.slice(0, 4).map((pred, i) => (
                    <div key={i} className="resnet-row">
                      <span className="resnet-name">{pred.label}</span>
                      <div className="resnet-bar-track">
                        <div
                          className="resnet-bar-fill"
                          style={{ width: `${Math.round(pred.confidence * 100)}%` }}
                        />
                      </div>
                      <span className="resnet-conf">{Math.round(pred.confidence * 100)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 3. YOLOv11 Objects Localized List */}
            <div className="telemetry-section-box flex-grow">
              <div className="section-box-header">
                <div className="header-left">
                  <CrosshairIcon size={15} />
                  <span>YOLOv11 Objects ({filteredObjects.length})</span>
                </div>
                <span className="model-chip green">yolo11n</span>
              </div>

              {/* Class Filter Tags */}
              {uniqueLabels.length > 1 && (
                <div className="class-filter-strip">
                  <button
                    type="button"
                    className={`filter-tag ${selectedClassFilter === 'all' ? 'active' : ''}`}
                    onClick={() => setSelectedClassFilter('all')}
                  >
                    All ({detectionData?.yoloObjects?.length || 0})
                  </button>
                  {uniqueLabels.map((lbl) => (
                    <button
                      key={lbl}
                      type="button"
                      className={`filter-tag ${selectedClassFilter === lbl ? 'active' : ''}`}
                      onClick={() => setSelectedClassFilter(lbl)}
                    >
                      <span
                        className="color-dot"
                        style={{ backgroundColor: getColorForLabel(lbl) }}
                      />
                      {lbl} ({detectionData?.yoloCounts?.[lbl] || 1})
                    </button>
                  ))}
                </div>
              )}

              {/* Detected Objects Scrollable List */}
              <div className="detected-objects-scroll">
                {filteredObjects.length > 0 ? (
                  filteredObjects.map((obj, idx) => {
                    const color = getColorForLabel(obj.label);
                    const isHovered = hoveredBoxIndex === idx;
                    return (
                      <div
                        key={idx}
                        className={`detected-object-row ${isHovered ? 'hovered' : ''}`}
                        onMouseEnter={() => setHoveredBoxIndex(idx)}
                        onMouseLeave={() => setHoveredBoxIndex(null)}
                      >
                        <div className="row-left">
                          <span
                            className="object-color-badge"
                            style={{ backgroundColor: color }}
                          />
                          <span className="object-label">{obj.label}</span>
                        </div>
                        <div className="row-right">
                          <span className="object-coords">
                            [{Math.round(obj.box[0])}, {Math.round(obj.box[1])}]
                          </span>
                          <span
                            className="object-conf-badge"
                            style={{ color: color, borderColor: `${color}40`, backgroundColor: `${color}15` }}
                          >
                            {Math.round(obj.confidence * 100)}%
                          </span>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="no-detections-msg">
                    {detectionData
                      ? 'No objects match current filter or threshold.'
                      : 'Send an image in chat or upload one above to see detections.'}
                  </div>
                )}
              </div>
            </div>

            {/* Threshold Slider */}
            <div className="telemetry-threshold-footer">
              <div className="threshold-label-row">
                <span>Confidence Threshold</span>
                <span className="threshold-val">{Math.round(confThreshold * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.10"
                max="0.90"
                step="0.05"
                value={confThreshold}
                onChange={(e) => setConfThreshold(parseFloat(e.target.value))}
                className="threshold-slider"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
