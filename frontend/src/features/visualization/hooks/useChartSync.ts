import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { createConnectedGroupId } from '../charts/echarts/configFactory';

export function useChartSync(enabled: boolean = true) {
  const groupIdRef = useRef<string>(createConnectedGroupId());

  useEffect(() => {
    if (!enabled) return;
    const groupId = groupIdRef.current;
    echarts.connect(groupId);

    return () => {
      echarts.disconnect(groupId);
    };
  }, [enabled]);

  return groupIdRef.current;
}
