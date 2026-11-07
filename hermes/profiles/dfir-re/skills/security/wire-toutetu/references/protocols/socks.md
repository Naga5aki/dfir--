---
knowledge_id: protocols.socks
title: SOCKS4/5 控制面
signals: [socks, socks5, proxy]
read_when: 出现 SOCKS 握手或代理链时。
support_status: best-effort
---

# SOCKS4/5 控制面

## 读取时机

出现 SOCKS 握手或代理链时。

## 版本矩阵

- 当前等级：`best-effort`；只有实际夹具通过才晋级。
- 先读取 `preflight` 的平台、TShark 版本和字段能力；4.4/4.6 差异走动态探测。

## 观察特征

版本、认证方法、CONNECT/BI