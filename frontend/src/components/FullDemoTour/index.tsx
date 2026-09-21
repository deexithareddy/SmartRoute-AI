import React, { useState, useEffect, useRef } from 'react';
import { AnalyzeResponseDTO } from '../../types/route';
import apiService from '../../services/api';

export interface DemoTourStep {
  stepNumber: number;
  title: string;
  subtitle: string;
  currentCondition: string;
  risk: string;
  recommendation: string;
  reason: string;
  dataConfidence: string;
  confidenceColor: string;
  scenarioId?: string;
  actionType: string;
  presenterNotes: string;
}

export const DEMO_TOUR_STEPS: DemoTourStep[] = [
  {
    stepNumber: 1,
    title: '1. Enter Emergency Source & Destination',
    subtitle: 'Corridor Initialization & Real Geocoding',
    currentCondition: 'Origin: Indiranagar General Hospital | Destination: Whitefield Trauma Center (Bengaluru)',
    risk: 'Baseline Nominal (Evaluating multi-route vector graph)',
    recommendation: 'Initializing OSRM candidate routes',
    reason: 'Evaluating high-precision OpenStreetMap vector corridors connecting critical trauma facilities',
    dataConfidence: 'HIGH (95%)',
    confidenceColor: '#10b981',
    scenarioId: 'scenario_1',
    actionType: 'scenario_1',
    presenterNotes: 'Showcase real Nominatim geocoding and vector route generation between emergency hospitals.',
  },
  {
    stepNumber: 2,
    title: '2. Select Ambulance + Critical Priority',
    subtitle: 'Vehicle Mission Profile Weighting',
    currentCondition: 'Vehicle: Ambulance | Priority: Critical Code-1 (Speed Weight W_t = 0.55)',
    risk: 'Speed-Optimized Risk Weighting Applied (Safety W_r = 0.25, Delay W_d = 0.10, Rel W_l = 0.10)',
    recommendation: 'Optimization Profile: Ambulance / Critical',
    reason: 'Acute emergency profile prioritizes minimum arrival time for time-sensitive resuscitation',
    dataConfidence: 'HIGH (95%)',
    confidenceColor: '#10b981',
    scenarioId: 'scenario_1',
    actionType: 'scenario_1',
    presenterNotes: 'Explain how mission profile presets dynamically adjust multi-criteria optimization weights.',
  },
  {
    stepNumber: 3,
    title: '3. Show Initial Recommended Route',
    subtitle: 'Normal Baseline Conditions (Route A Selected)',
    currentCondition: 'Clear weather (0 mm rain), smooth free-flow traffic (48 km/h), zero CAD incidents',
    risk: 'Route A (14% Low Risk) vs Route B (18% Low Risk)',
    recommendation: 'Route A (Direct Arterial) — 16 min ETA [RECOMMENDED]',
    reason: 'Lowest combined route score (0.12); fastest transit time under baseline clear conditions',
    dataConfidence: 'HIGH (95%)',
    confidenceColor: '#10b981',
    scenarioId: 'scenario_1',
    actionType: 'scenario_1',
    presenterNotes: 'Under clear conditions with all sensors online, the direct arterial is fastest and safest.',
  },
  {
    stepNumber: 4,
    title: '4. Introduce Severe Traffic Anomaly',
    subtitle: 'Sudden Speed Collapse & Cause-Agnostic Guard',
    currentCondition: 'Route A speed drops suddenly to 12.0 km/h (speed ratio 0.27). Cause: UNKNOWN',
    risk: 'Route A Traffic Risk surges to 78% (Overall Risk 48% MODERATE)',
    recommendation: 'Evaluating Bypass Corridors...',
    reason: 'Strict Cause Honesty: Anomaly reported as UNKNOWN because no CAD police incident confirms a collision',
    dataConfidence: 'HIGH (95%)',
    confidenceColor: '#10b981',
    scenarioId: 'scenario_2',
    actionType: 'scenario_2',
    presenterNotes: 'Highlight zero hallucination: the system never invents accident causes without CAD proof.',
  },
  {
    stepNumber: 5,
    title: '5. Show Recommendation Change',
    subtitle: 'Dynamic Rerouting to Route B Bypass',
    currentCondition: 'Route A bottlenecked with +16.5 min ML predicted delay',
    risk: 'Route B (18% Risk) vs Route A (48% Risk)',
    recommendation: 'Route B (Varthur Bypass) — 19 min ETA [RECOMMENDED]',
    reason: '10 minutes FASTER than bottlenecked Route A; 63% lower traffic congestion risk',
    dataConfidence: 'HIGH (95%)',
    confidenceColor: '#10b981',
    scenarioId: 'scenario_2',
    actionType: 'scenario_2',
    presenterNotes: 'The optimizer automatically flips to the bypass, circumventing the traffic bottleneck.',
  },
  {
    stepNumber: 6,
    title: '6. Introduce Heavy Rainfall & Storm',
    subtitle: 'Meteorological Hazard Exposure',
    currentCondition: 'Doppler radar detects 45 mm/h downpour, 52 km/h wind gusts, 800m visibility',
    risk: 'Surface underpasses on Route A face extreme waterlogging (Weather Risk 78%)',
    recommendation: 'Evaluating Elevated Infrastructure...',
    reason: 'Low-lying underpass roads vulnerable to rapid flash flood overtopping and tire hydroplaning',
    dataConfidence: 'HIGH (95%)',
    confidenceColor: '#10b981',
    scenarioId: 'scenario_3',
    actionType: 'scenario_3',
    presenterNotes: 'Open-Meteo live weather data samples all coordinates along route polylines.',
  },
  {
    stepNumber: 7,
    title: '7. Run What-If Scenario Simulation Sandbox',
    subtitle: 'Isolated Stress Testing without Live Database Mutation',
    currentCondition: 'Simulated Stress Test: +45 mm/h rain, 1.8x traffic multiplier, arterial closure check',
    risk: 'Route A (64% - 100% Extreme Hazard) vs Route B (26% Moderate Risk)',
    recommendation: 'Route B (Elevated Expressway Bypass)',
    reason: 'Isolated sandbox predicts weather friction and capacity loss without altering live telemetry feeds',
    dataConfidence: 'HIGH (95%)',
    confidenceColor: '#10b981',
    scenarioId: 'scenario_3',
    actionType: 'scenario_3',
    presenterNotes: 'Stress-test emergency scenarios without corrupting or modifying active operations data.',
  },
  {
    stepNumber: 8,
    title: '8. Show Route Ranking Change',
    subtitle: 'Elevated Corridor Selected for Drainage Resilience',
    currentCondition: 'Route A waterlogged / impassable in low sections; Route B elevated above flood line',
    risk: 'Route B (26% Composite Risk) vs Route A (64% Risk)',
    recommendation: 'Route B (Elevated Expressway) — 22 min ETA [RECOMMENDED]',
    reason: 'Elevated structure provides active drainage resilience, avoiding submerged surface intersections',
    dataConfidence: 'HIGH (95%)',
    confidenceColor: '#10b981',
    scenarioId: 'scenario_3',
    actionType: 'scenario_3',
    presenterNotes: 'Elevated corridor resilience ensures emergency vehicle arrival despite torrential rains.',
  },
  {
    stepNumber: 9,
    title: '9. Disable Traffic Data (Fault Injection)',
    subtitle: 'Simulating Sensor Outage & Network Failure',
    currentCondition: 'Municipal speed sensor grid forced UNAVAILABLE (Simulated API communication loss)',
    risk: 'Traffic risk reverts to historical baseline; certainty degraded',
    recommendation: 'Recalculating with Partial Telemetry...',
    reason: 'Zero Crash Guarantee: System isolates failed sensor and continues operating safely',
    dataConfidence: 'MODERATE (75%) [DEGRADED]',
    confidenceColor: '#f59e0b',
    scenarioId: 'scenario_6',
    actionType: 'scenario_6',
    presenterNotes: 'Demonstrate fault-injection: when traffic sensors die, SmartRoute AI never crashes.',
  },
  {
    stepNumber: 10,
    title: '10. Show Reduced Confidence & ML Rule Fallback',
    subtitle: 'Graceful Degradation & Heuristic Estimation',
    currentCondition: 'Traffic Feed Offline — Hybrid delay regressor suppresses ML inference',
    risk: 'Route A (32% Risk) vs Route B (35% Risk) evaluated with missing speed data',
    recommendation: 'Route A (Deterministic Fallback) — 18 min ETA [RECOMMENDED]',
    reason: 'Predictor automatically switches to ⚙️ Rule-Based Heuristic (+2.5m); UI warns of reduced certainty',
    dataConfidence: 'MODERATE (75%)',
    confidenceColor: '#f59e0b',
    scenarioId: 'scenario_6',
    actionType: 'scenario_6',
    presenterNotes: 'Explain the hybrid ML architecture: partial data triggers transparent rule-based heuristics.',
  },
  {
    stepNumber: 11,
    title: '11. Display Final Grounded Explanation',
    subtitle: 'Transparent Explainable AI Rationale',
    currentCondition: 'Comprehensive mathematical audit across speed, risk, delay, and reliability factors',
    risk: 'Traffic 30% | Weather 10% | Incident 0% | Road 20%',
    recommendation: 'Full Decision Audit Rendered in UI',
    reason: 'Mathematically verified bullet points explain both why Route A won and why other corridors were rejected',
    dataConfidence: 'MODERATE (75%)',
    confidenceColor: '#f59e0b',
    scenarioId: 'scenario_6',
    actionType: 'scenario_6',
    presenterNotes: 'Review the Grounded Decision Rationale: complete mathematical transparency with zero invented reasons.',
  },
  {
    stepNumber: 12,
    title: '12. Restore Normal Conditions',
    subtitle: 'System Recovery & Live Telemetry Restored',
    currentCondition: 'All sensors reconnected, fault injection cleared, live telemetry streaming online',
    risk: 'Route A (14% Low Risk) vs Route B (18% Low Risk)',
    recommendation: 'Route A (Direct Arterial) — 16 min ETA [RECOMMENDED]',
    reason: 'Full operational recovery: ambulance routed along optimal clear highway with 95% data confidence',
    dataConfidence: 'HIGH (95%)',
    confidenceColor: '#10b981',
    scenarioId: 'scenario_1',
    actionType: 'reset',
    presenterNotes: 'The demo tour concludes with full live telemetry restored and verified.',
  },
];

interface FullDemoTourProps {
  isOpen: boolean;
  onClose: () => void;
  onApplyScenario: (result: AnalyzeResponseDTO, scenarioName: string) => void;
  onResetLive: () => void;
  vehicleType?: string;
  priority?: string;
}

export const FullDemoTour: React.FC<FullDemoTourProps> = ({
  isOpen,
  onClose,
  onApplyScenario,
  onResetLive,
  vehicleType = 'Ambulance',
  priority = 'Critical',
}) => {
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const stepTimerSeconds = 8; // seconds per step (configurable)
  const [secondsRemaining, setSecondsRemaining] = useState<number>(stepTimerSeconds);
  const timerRef = useRef<number | null>(null);

  const currentStep = DEMO_TOUR_STEPS[currentStepIndex];

  // Execute scenario when step changes
  useEffect(() => {
    if (!isOpen) return;

    const executeStepAction = async () => {
      try {
        if (currentStep.actionType === 'reset') {
          await apiService.resetDemoMode();
          onResetLive();
        } else if (currentStep.scenarioId) {
          const res = await apiService.activateDemoScenario(
            currentStep.scenarioId,
            vehicleType,
            priority
          );
          if (res && res.analyze_result) {
            onApplyScenario(res.analyze_result, res.scenario_name);
          }
        }
      } catch (err) {
        console.error('Error executing demo tour step:', err);
      }
    };

    executeStepAction();
    setSecondsRemaining(stepTimerSeconds);
  }, [currentStepIndex, isOpen]);

  // Auto-play timer
  useEffect(() => {
    if (!isOpen || !isPlaying) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    timerRef.current = window.setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          // Advance to next step or loop/stop
          setCurrentStepIndex((currIdx) => {
            if (currIdx < DEMO_TOUR_STEPS.length - 1) {
              return currIdx + 1;
            } else {
              setIsPlaying(false);
              return currIdx;
            }
          });
          return stepTimerSeconds;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isOpen, isPlaying, stepTimerSeconds]);

  if (!isOpen) return null;

  const handleNext = () => {
    if (currentStepIndex < DEMO_TOUR_STEPS.length - 1) {
      setCurrentStepIndex(currentStepIndex + 1);
    }
  };

  const handlePrev = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(currentStepIndex - 1);
    }
  };

  const handleStepJump = (idx: number) => {
    setCurrentStepIndex(idx);
  };

  const progressPercent = ((currentStepIndex + 1) / DEMO_TOUR_STEPS.length) * 100;
  const timeProgress = ((stepTimerSeconds - secondsRemaining) / stepTimerSeconds) * 100;

  return (
    <div className="demo-tour-modal-backdrop">
      <div className="demo-tour-hud-card">
        {/* Top Header Bar */}
        <div className="tour-hud-header">
          <div className="tour-brand-group">
            <span className="tour-badge-pill">🎬 GUIDED SIH DEMO TOUR</span>
            <span className="tour-step-counter">
              Step <strong>{currentStepIndex + 1}</strong> of <strong>{DEMO_TOUR_STEPS.length}</strong>
            </span>
          </div>

          <div className="tour-playback-controls">
            <button
              type="button"
              className={`tour-play-btn ${isPlaying ? 'is-playing' : ''}`}
              onClick={() => setIsPlaying(!isPlaying)}
              title={isPlaying ? 'Pause Auto-Advance' : 'Play Auto-Advance'}
            >
              {isPlaying ? '⏸ Pause' : '▶ Auto-Play'}
            </button>

            <button
              type="button"
              className="tour-nav-btn"
              onClick={handlePrev}
              disabled={currentStepIndex === 0}
              title="Previous Step"
            >
              ◀ Prev
            </button>

            <button
              type="button"
              className="tour-nav-btn"
              onClick={handleNext}
              disabled={currentStepIndex === DEMO_TOUR_STEPS.length - 1}
              title="Next Step"
            >
              Next ▶
            </button>

            <button
              type="button"
              className="tour-close-btn"
              onClick={() => {
                onResetLive();
                onClose();
              }}
              title="Exit Demo Tour"
            >
              ✕ Exit
            </button>
          </div>
        </div>

        {/* Global Tour Progress Bar */}
        <div className="tour-progress-track">
          <div className="tour-progress-fill" style={{ width: `${progressPercent}%` }}></div>
          {isPlaying && (
            <div
              className="tour-time-bar"
              style={{ width: `${timeProgress}%` }}
            ></div>
          )}
        </div>

        {/* Step Navigation Dots */}
        <div className="tour-step-chips">
          {DEMO_TOUR_STEPS.map((_s, idx) => (
            <button
              key={idx}
              type="button"
              className={`step-chip ${idx === currentStepIndex ? 'active' : ''} ${
                idx < currentStepIndex ? 'completed' : ''
              }`}
              onClick={() => handleStepJump(idx)}
            >
              {idx + 1}
            </button>
          ))}
        </div>

        {/* Step Title & Subtitle */}
        <div className="tour-step-title-row">
          <div>
            <h3 className="tour-step-title">{currentStep.title}</h3>
            <span className="tour-step-sub">{currentStep.subtitle}</span>
          </div>
          {isPlaying && (
            <span className="tour-countdown-pill">
              ⏱ Next in {secondsRemaining}s
            </span>
          )}
        </div>

        {/* 5-Stage Live Information Card */}
        <div className="tour-metrics-grid">
          {/* 1. CURRENT CONDITION */}
          <div className="metric-box box-condition">
            <span className="metric-tag">📌 CURRENT CONDITION</span>
            <p className="metric-value">{currentStep.currentCondition}</p>
          </div>

          {/* 2. RISK */}
          <div className="metric-box box-risk">
            <span className="metric-tag">⚠️ RISK</span>
            <p className="metric-value">{currentStep.risk}</p>
          </div>

          {/* 3. RECOMMENDATION */}
          <div className="metric-box box-rec">
            <span className="metric-tag">⭐ RECOMMENDATION</span>
            <p className="metric-value metric-rec-bold">{currentStep.recommendation}</p>
          </div>

          {/* 4. REASON */}
          <div className="metric-box box-reason">
            <span className="metric-tag">💡 REASON</span>
            <p className="metric-value">{currentStep.reason}</p>
          </div>

          {/* 5. DATA CONFIDENCE */}
          <div className="metric-box box-confidence">
            <span className="metric-tag">🛡️ DATA CONFIDENCE</span>
            <p className="metric-value" style={{ color: currentStep.confidenceColor }}>
              <strong>{currentStep.dataConfidence}</strong>
            </p>
          </div>
        </div>

        {/* Presenter Talk-Track Note */}
        <div className="tour-presenter-note">
          <span className="note-icon">🎙️</span>
          <span className="note-text">
            <strong>Presenter Cue:</strong> {currentStep.presenterNotes}
          </span>
        </div>
      </div>
    </div>
  );
};

export default FullDemoTour;
