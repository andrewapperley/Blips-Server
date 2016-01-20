# Reset password link
kResetPasswordLink = "%s/user/reset_password/confirm?username=%s&token=%s&device_token=%s&request_timestamp=%s&new_password="

kResetPasswordTemplateName = '/reset_password/reset_password.html'
kResetPasswordConfirmation = 'Your password has been reset, you may proceed to login to Blips!'
kResetPasswordError = 'An error occurred while processing your request.'
kResetPasswordSubject = 'Requested Password Reset'

# Welcome email
kWelcomeEmail = """\
            <html>
                <head>
                    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
                    <title>Welcome To Blips</title>
                </head>
                <body>
                    <center><img alt="Blips Logo" src="cid:logoImage" width="280" height="117" /></center>
                    <p>%s, thank you for signing up for Blips! We really hope that you enjoy the app as much as we do on a
                     daily basis.<br><br>
                     If you have any questions about the app or comments regarding your experience please send an email
                     using the feedback button on the left panel of Blips and we will be sure to get back to you as soon as
                     possible, also check out the FAQ section for further information.
                    </p>
                </body>
            </html>
                """
kWelcomeEmailSubject = 'Welcome to Blips'

# Email message for reset password
kEmailResetResponseMessage = """\
            <html>
                <head>
                    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
                    <title>Welcome To Blips</title>
                </head>
                <body>
                    <center><img alt="Blips Logo" src="cid:logoImage" width="280" height="117" /></center>
                    <p>Click link to reset your password: <a href="%s">Reset Link</a>
                    </p>
                </body>
            </html>
                """

# Email Types:
## Reset Password Type
kEmailTypeReset = 'reset_password'
## Generic Type
kEmailTypeGeneric = 'generic'

# Date Formatter
kDateFormatFullDate = '%Y-%d-%m %H:%M:%S'
kDateFormatMinimalDate = '%Y-%m-%d'
kDateFormat1900Date = '1900-01-01'

# Server Responses

## HTTP Error Responses
kServerGeneric500Error = 'The server ran into an issue, try your request again please!'
kServer503Error = 'The server cannot handle your request at this time, try again later!'
kServer500Error = 'The server ran into an issue, try your request again please!'
kServer408Error = 'Your request timed-out, please try again!'
kServer406Error = 'That was unacceptable, never attempt that again!'
kServer405Error = 'The method you attempted to access could not be found, please try again!'
kServer404Error = 'The resource you attempted to access could not be found, please try again!'
kServer403Error = 'That is forbidden!'
kServer401Error = 'You are unauthorized to access that resource!'
kServer400Error_WithMessage = 'The %s parameter is missing, please provide it and try again!'
kServer400Error_WithoutMessage = 'There is a parameter missing, please provide it and try again!'

## Authorization Error Responses
kServerAuthorizeUserNotActive = 'Access Denied - User not active'
kServerAuthorizeUserDoesntExist = 'Access Denied - User does not exist'
kServerAuthorizeUserDeactivated = 'Access Denied - User is deactivated.'
kServerAuthorizeWrongParamsSent = 'Required parameters not sent, please try again.'
kServerAuthorizeDatabaseError = 'There was a database error, please try again.'

## Video Responses
kServerVideoAlreadyExistsError = 'kServerVideoAlreadyExistsError'
kServerVideoDoesntExistError = 'kServerVideoDoesntExistError'
kServerVideoFutureVideoError = 'kServerVideoFutureVideoError'
kServerVideoBefore1900Error = 'kServerVideoBefore1900Error'
kServerVideoTimelineIDDoesntExist = 'kServerVideoTimelineIDDoesntExist'
kServerVideoIssueMakingVideo = 'kServerVideoIssueMakingVideo'
kServerVideoCreatedVideoSuccess = 'kServerVideoCreatedVideoSuccess'
kServerVideoVideosForPage = 'kServerVideoVideosForPage'
kServerVideoTimelineIDsForUser = 'kServerVideoTimelineIDsForUser'
kServerVideoTimelineIDsForUserFailure = 'kServerVideoTimelineIDsForUserFailure'
kServerVideoSetVideoToWatchFailure = 'kServerVideoSetVideoToWatchFailure'
kServerVideoSetVideoToWatchSuccess = 'kServerVideoSetVideoToWatchSuccess'
kServerVideoAlreadyFavourited = 'kServerVideoAlreadyFavourited'
kServerVideoFavouritingError = 'kServerVideoFavouritingError'
kServerVideoFavouritedSuccess = 'kServerVideoFavouritedSuccess'
kServerVideoNotFavourited = 'kServerVideoNotFavourited'
kServerFavouriteRemovedSuccess = 'kServerFavouriteRemovedSuccess'
kServerVideoUserHasNoFavourites = 'kServerVideoUserHasNoFavourites'
kServerVideoTimelineCreationError = 'kServerVideoTimelineCreationError'
kServerVideoTimelineCreationSuccess = 'kServerVideoTimelineCreationSuccess'
kServerVideoTimelineList = 'kServerVideoTimelineList'
kServerVideoAlreadyFlagged = 'kServerVideoAlreadyFlagged'
kServerVideoFlaggedSuccessfully = 'kServerVideoFlaggedSuccessfully'
kServerVideoUnFlaggedSuccessfully = 'kServerVideoUnFlaggedSuccessfully'
kServerVideoDeletedSuccessfully = 'kServerVideoDeletedSuccessfully'
kServerVideoPrivateSuccessfully = 'kServerVideoPrivateSuccessfully'
kServerVideoPrivateFailed = 'kServerVideoPrivateFailed'

## User Responses
kServerUserCreationError = 'kServerUserCreationError'
kServerUserAlreadyExistsError = 'kServerUserAlreadyExistsError'
kServerUserSignUpSuccess = 'kServerUserSignUpSuccess'
kServerUserNotFoundError = 'kServerUserNotFoundError'
kServerUserInfoResponseSuccess = 'kServerUserInfoResponseSuccess'
kServerUserInfoUpdatedSuccess = 'kServerUserInfoUpdatedSuccess'
kServerUserAlreadyDeactivatedError = 'kServerUserAlreadyDeactivatedError'
kServerDeactivatedNotAuthorizedError = 'kServerDeactivatedNotAuthorizedError'
kServerUserDeactivatedSuccess = 'kServerUserDeactivatedSuccess'
kServerUserUpdateNoInfoToUpdateError = 'kServerUserUpdateNoInfoToUpdateError'
kServerUserTokenUpdatedSuccess = 'Users token updated successfully'
kServerUserUsernameAvailableSuccess = 'kServerUserTokenUpdatedSuccess'
kServerUserUsernameAvailableError = 'kServerUserUsernameAvailableError'
kServerUserLoggedOutSuccess = 'kServerUserLoggedOutSuccess'
kServerUserLoggedOutError = 'kServerUserLoggedOutError'
kServerUserLoggedInSuccess = 'kServerUserLoggedInSuccess'
kServerUserLoggedInError = 'kServerUserLoggedInError'
kServerUserConnectionRequestSentSuccess = 'kServerUserConnectionRequestSentSuccess'
kServerUserConnectionRemoveProfileSuccess = 'kServerUserConnectionRemoveProfileSuccess'
kServerUserConnectionRemoveProfileFailure = 'kServerUserConnectionRemoveProfileFailure'
kServerUserConnectionRequestExistsError = 'kServerUserConnectionRequestExistsError'
kServerUserConnectionRequestSentError = 'kServerUserConnectionRequestSentError'
kServerUserAcceptConnectionRequestError = 'kServerUserAcceptConnectionRequestError'
kServerUserAcceptConnectionRequestSuccess = 'kServerUserAcceptConnectionRequestSuccess'
kServerUserConnectionListSuccess = 'kServerUserConnectionListSuccess'
kServerUserConnectionProfileSuccess = 'kServerUserConnectionProfileSuccess'
kServerUserConnectionProfileError = 'kServerUserConnectionProfileError'
kServerUserConnectionListError = 'kServerUserConnectionListError'
kServerUserLimitedProfileSuccess = 'kServerUserLimitedProfileSuccess'
kServerUserLimitedProfileError = 'kServerUserLimitedProfileError'
kServerUserSearchResponse = 'kServerUserSearchResponse'
kServerUserPasswordResetRequestError = 'User didn\'t request a password reset.'
kServerUserPasswordResetUserDoesNotExistRequestError = 'kServerUserPasswordResetUserDoesNotExistRequestError'
kServerUserPasswordResetRequestAlreadyPresent = 'Pending password reset already present.'
kServerUserPasswordRequestSentSuccess = 'A password reset link has been sent to the email you signed up with.'
kServerReceiptsResponse = 'kServerReceiptsResponse'
kServerReceiptsPostResponse = 'kServerReceiptsPostResponse'

## Notification Responses
kServerUserRegisteredForNotificationSuccess = 'kServerUserRegisteredForNotificationSuccess'
kServerListNotificationSuccess = 'kServerListNotificationSuccess'
kServerUserUnregisterNotificationSuccess = 'kServerUserUnregisterNotificationSuccess'
kServerUserUnregisterNotificationFailure = 'kServerUserUnregisterNotificationFailure'
kServerNotificationReadSuccess = 'kServerNotificationReadSuccess'

## Notification Constants
### Types
kServerNotificationsType = 'NotificationType'
kServerNotificationsTypeConnectionsRequest = 0
kServerNotificationsTypeConnectionsRequestConfirmation = 1
kServerNotificationsTypeNewVideo = 2
kServerNotificationsTypeConnectionsRequestTitle = "%s sent you a new connection request"
kServerNotificationsTypeConnectionsRequestConfirmationTitle = "%s confirmed your connection request"
kServerNotificationsTypeNewVideoTitle = "%s sent you a new video"
### Keys
kServerNotificationsUser_idKey = 'user_id'
kServerNotificationsUser_NameKey = 'display_name'
kServerNotificationsConnection_idKey = 'connection_id'
kServerNotificationsTimeline_idKey = 'timeline_id'

## AWS S3
AWS_ACCESS_KEY_ID = ''
AWS_SECRET_KEY = ''
AWS_BUCKET_NAME = ''

## Public Feed
kServerVideoPublicFeedKey = '__PUBLIC_FEED__'
