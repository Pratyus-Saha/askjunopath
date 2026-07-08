/**
 * Heuristics for determining window event types since the engine currently
 * only provides a flat list of event types at the domain level.
 * 
 * Tradeoffs: 
 * 1. Checks if any window trigger matches a known blocking factor (cleanest match).
 * 2. If no window has a clean match, falls back to marking the lowest scoring window
 *    as "caution" IF there are 3+ windows.
 * 3. The remaining windows are split roughly evenly between "advancement" and 
 *    "steady-progress" based on their score rank.
 */

export function getWindowEventType(
  window: any,
  engineOutput: any
): "advancement" | "steady-progress" | "caution" {
  const blockingFactors = engineOutput.blocking_factors || [];
  
  // 1. Clean match check
  let isCaution = false;
  if (blockingFactors.length > 0 && window.triggers) {
    for (const trigger of window.triggers) {
      for (const factor of blockingFactors) {
        if (
          trigger.planet === factor.source && 
          trigger.natal_point === `cusp_${factor.house}`
        ) {
          isCaution = true;
          break;
        }
      }
      if (isCaution) break;
    }
  }
  
  // If we have a direct match, return caution immediately
  if (isCaution) return "caution";

  // Check if ANY window in the whole payload has a direct match
  const windows = engineOutput.transit_windows || [];
  let anyWindowHasMatch = false;
  if (blockingFactors.length > 0) {
    for (const w of windows) {
      if (w.triggers) {
        for (const trigger of w.triggers) {
          for (const factor of blockingFactors) {
            if (
              trigger.planet === factor.source && 
              trigger.natal_point === `cusp_${factor.house}`
            ) {
              anyWindowHasMatch = true;
              break;
            }
          }
          if (anyWindowHasMatch) break;
        }
      }
      if (anyWindowHasMatch) break;
    }
  }

  // 2. Fallback if no window had a match and we have 3+ windows
  if (!anyWindowHasMatch && windows.length >= 3) {
    // find the window with the lowest score
    let lowestScoreWindow = windows[0];
    for (const w of windows) {
      if (w.window_score < lowestScoreWindow.window_score) {
        lowestScoreWindow = w;
      }
    }
    // If THIS window is the lowest score one, it's caution
    if (window === lowestScoreWindow) {
      return "caution";
    }
  }

  // 3. Score ranking for remaining non-caution types
  const nonCautionWindows = windows.filter((w: any) => {
    let wIsCaution = false;
    if (blockingFactors.length > 0 && w.triggers) {
      for (const trigger of w.triggers) {
        for (const factor of blockingFactors) {
          if (
            trigger.planet === factor.source && 
            trigger.natal_point === `cusp_${factor.house}`
          ) {
            wIsCaution = true;
            break;
          }
        }
        if (wIsCaution) break;
      }
    }
    if (!anyWindowHasMatch && windows.length >= 3) {
      let lowestScoreWindow = windows[0];
      for (const cw of windows) {
        if (cw.window_score < lowestScoreWindow.window_score) {
          lowestScoreWindow = cw;
        }
      }
      if (w === lowestScoreWindow) {
        wIsCaution = true;
      }
    }
    return !wIsCaution;
  });

  // Sort them by score descending
  nonCautionWindows.sort((a: any, b: any) => b.window_score - a.window_score);

  // We are currently processing `window`. Find its rank.
  const rankIndex = nonCautionWindows.indexOf(window);
  
  if (rankIndex === -1) {
    // Should never happen unless window is not in the array and somehow bypassed caution logic
    return "steady-progress";
  }

  // Top half is advancement, bottom half is steady-progress
  const cutoff = Math.ceil(nonCautionWindows.length / 2);
  
  if (rankIndex < cutoff) {
    return "advancement";
  }
  return "steady-progress";
}
