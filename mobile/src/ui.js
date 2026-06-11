// 공용 RN 컴포넌트 — 웹 Ui.jsx와 동일한 시각 언어
import React from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';
import { C } from './theme';

export function Card({ children, style, pad = 16 }) {
  return (
    <View style={[{ backgroundColor: C.card, borderRadius: 20, padding: pad }, style]}>
      {children}
    </View>
  );
}

export function Hero({ color, children }) {
  return (
    <View style={{ borderRadius: 26, padding: 22, overflow: 'hidden', backgroundColor: color,
      shadowColor: color, shadowOpacity: 0.35, shadowRadius: 16, shadowOffset: { width: 0, height: 8 } }}>
      <View style={{ position: 'absolute', right: -40, top: -40, width: 180, height: 180,
        borderRadius: 90, backgroundColor: 'rgba(255,255,255,0.14)' }} />
      {children}
    </View>
  );
}

export function SectionLabel({ children }) {
  return <Text style={{ fontSize: 13, fontWeight: '600', letterSpacing: 0.3, textTransform: 'uppercase',
    color: C.label2, marginHorizontal: 4, marginBottom: 10 }}>{children}</Text>;
}

export function CTA({ children, onPress, variant = 'filled', busy, disabled }) {
  const bg = { filled: C.tint, gray: C.fill2, tinted: 'rgba(10,132,255,0.15)' }[variant] || C.tint;
  const fg = variant === 'tinted' ? C.tint : variant === 'gray' ? C.label : '#fff';
  return (
    <Pressable onPress={onPress} disabled={disabled || busy}
      style={({ pressed }) => ({ backgroundColor: bg, borderRadius: 16, paddingVertical: 15,
        alignItems: 'center', flexDirection: 'row', justifyContent: 'center', gap: 8,
        opacity: disabled || busy ? 0.55 : pressed ? 0.85 : 1 })}>
      {busy && <ActivityIndicator color={fg} size="small" />}
      <Text style={{ color: fg, fontSize: 17, fontWeight: '600' }}>{children}</Text>
    </Pressable>
  );
}

export function Metric({ value, unit, label, size = 26, color = C.label }) {
  return (
    <View style={{ alignItems: 'center', flex: 1 }}>
      <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 3 }}>
        <Text style={{ fontSize: size, fontWeight: '700', color, fontVariant: ['tabular-nums'] }}>{value}</Text>
        {unit ? <Text style={{ fontSize: size * 0.45, fontWeight: '600', color: C.label2 }}>{unit}</Text> : null}
      </View>
      {label ? <Text style={{ fontSize: 11.5, fontWeight: '500', color: C.label3, marginTop: 4,
        textTransform: 'uppercase' }}>{label}</Text> : null}
    </View>
  );
}

export function RecoveryBadge({ level }) {
  const m = {
    high: { color: C.red, label: '회복 필요' },
    medium: { color: C.orange, label: '주의' },
    low: { color: C.green, label: '양호' },
  }[level] || { color: C.green, label: '양호' };
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, alignSelf: 'flex-start',
      backgroundColor: `${m.color}22`, borderRadius: 999, paddingVertical: 5, paddingHorizontal: 11 }}>
      <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: m.color }} />
      <Text style={{ color: m.color, fontSize: 13, fontWeight: '600' }}>{m.label}</Text>
    </View>
  );
}

export function Banner({ tone = 'info', children }) {
  const color = { info: C.tint, warn: C.orange, error: C.red }[tone];
  return (
    <View style={{ backgroundColor: `${color}1A`, borderRadius: 14, padding: 13 }}>
      <Text style={{ color: C.label, fontSize: 14 }}>{children}</Text>
    </View>
  );
}

export function Loading({ label }) {
  return (
    <View style={{ paddingVertical: 48, alignItems: 'center', gap: 12 }}>
      <ActivityIndicator color={C.tint} size="large" />
      {label ? <Text style={{ color: C.label2, fontSize: 15 }}>{label}</Text> : null}
    </View>
  );
}

export function Chip({ label, on, onPress, color = C.tint }) {
  return (
    <Pressable onPress={onPress} style={{ paddingVertical: 7, paddingHorizontal: 13, borderRadius: 999,
      backgroundColor: on ? color : C.fill }}>
      <Text style={{ color: on ? '#fff' : C.label2, fontSize: 14, fontWeight: '600' }}>{label}</Text>
    </Pressable>
  );
}
