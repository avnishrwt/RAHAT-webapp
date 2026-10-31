/**
 * RAHAT System Constants
 * Single source of truth for priority weights, status codes, and map coordinates.
 */

// Priority Levels with Dual Indicators (Color + Human Label)
export const PRIORITY_LEVELS = {
  CRIT: {
    label: 'CRITICAL',
    badgeClass: 'badge-crit',
    color: '#ef4444',
    minScore: 30,
    description: 'Life-threatening / immediate rescue needed'
  },
  HIGH: {
    label: 'HIGH',
    badgeClass: 'badge-high',
    color: '#f97316',
    minScore: 20,
    description: 'Urgent medical or vulnerable persons trapped'
  },
  MED: {
    label: 'MEDIUM',
    badgeClass: 'badge-med',
    color: '#eab308',
    minScore: 10,
    description: 'Resource request, moderate water logging'
  },
  LOW: {
    label: 'LOW',
    badgeClass: 'badge-low',
    color: '#38bdf8',
    minScore: 0,
    description: 'General query or non-urgent request'
  }
};

// Priority Calculation Weights (w1 to w5) as defined in PRD Section 6.1
export const PRIORITY_WEIGHTS = {
  medical: 3.0,     // w_1: Medical severity (Life-threatening, serious, minor)
  people: 1.5,      // w_2: Count of people at risk
  vulnerable: 2.5,  // w_3: Elderly, children, disabled, pregnant
  hazard: 2.0,      // w_4: Water level, fire, collapse, landslide
  waiting: 0.5      // w_5: Wait time multiplier (ensures no one waits forever)
};

// Default Geographic Coordinates for Rampur flood zone demo
export const DEFAULT_MAP_CENTER = [30.3165, 78.0322]; // Uttarakhand district region
export const DEFAULT_MAP_ZOOM = 13;

// Active Navigation Surfaces
export const SURFACES = {
  OPERATOR: 'operator',
  TEAM_PWA: 'team_pwa',
  SIMULATOR: 'simulator'
};

// Citizen Channels
export const CHANNELS = {
  WHATSAPP: 'whatsapp',
  SMS: 'sms',
  HELPLINE: 'helpline',
  VOICE: 'voice'
};
