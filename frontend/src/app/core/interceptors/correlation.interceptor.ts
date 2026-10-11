import { HttpInterceptorFn } from '@angular/common/http';

/** מוסיף X-Correlation-Id לכל בקשה (NFR-43) כדי שאפשר יהיה לעקוב אחריה בלוגים של השרת. */
export const correlationInterceptor: HttpInterceptorFn = (req, next) =>
  next(req.clone({ setHeaders: { 'X-Correlation-Id': crypto.randomUUID() } }));
