# State migration: resources moved from root into modules (no destroy/recreate)

# Auth module
moved {
  from = aws_iam_role.auth
  to   = module.auth.aws_iam_role.auth
}
moved {
  from = aws_iam_role_policy_attachment.auth_basic
  to   = module.auth.aws_iam_role_policy_attachment.auth_basic
}
moved {
  from = aws_lambda_function.auth
  to   = module.auth.aws_lambda_function.auth
}
moved {
  from = aws_apigatewayv2_api.auth
  to   = module.auth.aws_apigatewayv2_api.auth
}
moved {
  from = aws_apigatewayv2_integration.auth
  to   = module.auth.aws_apigatewayv2_integration.auth
}
moved {
  from = aws_apigatewayv2_route.get_token
  to   = module.auth.aws_apigatewayv2_route.get_token
}
moved {
  from = aws_apigatewayv2_stage.auth
  to   = module.auth.aws_apigatewayv2_stage.auth
}
moved {
  from = aws_lambda_permission.auth_api
  to   = module.auth.aws_lambda_permission.auth_api
}
