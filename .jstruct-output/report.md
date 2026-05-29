# mall 架构报告

生成时间: 2026-05-29T12:07:27.839039155Z

## 架构概览

- 模块数: 7
- 类数量: 519
- 关系数: 726
- 环依赖: 0

## 热点 Top10


| 排名 | 类 | 分数 |
|---:|---|---:|

| 1 | com.macro.mall.model.OmsOrderExample | 32.94 |

| 2 | com.macro.mall.model.PmsProductExample | 32.84 |

| 3 | com.macro.mall.portal.service.impl.OmsPortalOrderServiceImpl | 31.67 |

| 4 | com.macro.mall.model.OmsOrderReturnApplyExample | 21.54 |

| 5 | com.macro.mall.service.impl.PmsProductServiceImpl | 20.680000000000003 |

| 6 | com.macro.mall.model.OmsOrderItemExample | 17.24 |

| 7 | com.macro.mall.portal.service.impl.UmsMemberCouponServiceImpl | 17.090000000000003 |

| 8 | com.macro.mall.model.UmsMemberExample | 16.6 |

| 9 | com.macro.mall.model.PmsProduct | 16.46 |

| 10 | com.macro.mall.model.SmsCouponExample | 15.940000000000001 |



## A/I 模块矩阵


| 模块 | Ca | Ce | I | A | D | Zone |
|---|---:|---:|---:|---:|---:|---|

| mall-security | 2 | 1 | 0.33 | 0.07 | 0.60 | pain |

| mall-admin | 1 | 4 | 0.80 | 0.35 | 0.15 | normal |

| mall-search | - | - | 0.00 | 0.27 | 0.73 | pain |

| mall-mbg | 3 | - | 0.00 | 0.33 | 0.67 | pain |

| mall-demo | 1 | 1 | 0.50 | 0.08 | 0.42 | normal |

| mall-common | 3 | - | 0.00 | 0.14 | 0.86 | pain |

| mall-portal | - | 4 | 1.00 | 0.27 | 0.27 | normal |



## 重构建议


- 痛苦区模块需要降低具体依赖或提高抽象度: mall-security, mall-search, mall-mbg, mall-common。

- 最高热点 com.macro.mall.model.OmsOrderExample 建议优先做职责拆分和复杂度治理。
