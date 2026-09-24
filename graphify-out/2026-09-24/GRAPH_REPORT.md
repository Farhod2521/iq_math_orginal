# Graph Report - iq_math_orginal  (2026-09-24)

## Corpus Check
- Large corpus: 635 files · ~1,574,783 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 2585 nodes · 6448 edges · 206 communities (122 shown, 84 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 1028 edges (avg confidence: 0.95)
- Token cost: 147,947 input · 0 output

## Community Hubs (Navigation)
- App Student app
- App Student app
- App Management app
- App Unversial View app
- App Student - View
- App User app
- App Teacher app
- App Management - VIEW
- App Student app
- App User app
- App Management app
- App Tutor app
- App Tutor app
- App Payments app
- App User - VIEW
- App Student - View
- App Battle app
- App Student app
- App Battle app
- App Teacher app
- App Teacher app
- App Battle app
- App Management app
- App Tutor app
- App Student app
- App User app
- App Book app
- App Student - View
- App Student - View
- App Teacher - View
- App Student app
- App Battle app
- App Management app
- App Chat app
- App Payments - VIEW
- App Tutor app
- App User app
- App User app
- App Management app
- App Teacher - Commands
- App Tutor app
- App User app
- App Student - View
- App Battle app
- App User app
- App Chat app
- App Management - VIEW
- Converted
- Helped Bot
- App Book app
- App Management - VIEW
- App User app
- Bot Telegram
- App Book app
- App Teacher - View
- App Chat app
- App Chat app
- App Chat app
- App Management - VIEW
- App Student - View
- App Student - View
- App Battle app
- Bot Telegram
- App Chat app
- App Management - VIEW
- App Management - VIEW
- App Payments - VIEW
- App Tutor app
- App Chat app
- App Student - View
- App User app
- App Book app
- App Management - VIEW
- App Management - VIEW
- App Management - VIEW
- App Student app
- App Teacher app
- Bot Telegram
- App Tutor app
- App Management - VIEW
- Converted
- App Management app
- App Management - VIEW
- App Payments - VIEW
- App Payments - VIEW
- App Book app
- App Chat app
- App Payments app
- App Payments app
- App Teacher - View
- App Chat app
- App Battle app
- App Battle app
- App Book app
- App Book app
- App Chat app
- App Tutor app
- App User app
- App Battle app
- App Management app
- App Payments app
- App Payments app
- App Teacher app
- App Teacher app
- App Teacher app
- App Tutor app
- App User app
- App Book app
- App Book app
- App Chat app
- App Management - VIEW
- App Student app
- App Student - View
- App Teacher - View
- App Teacher - View
- App Tutor app
- App User app
- Testdoc
- App Book app
- Testdoc
- Settings
- App Book app
- App Payments app
- App Teacher - View
- App User app
- App User app
- App Management - VIEW
- App Teacher - View
- App Management - VIEW
- App Management - VIEW
- App Payments - VIEW
- App Payments - VIEW
- App Student - View
- App Student - View
- App Teacher - View
- App Battle app
- App Book app
- App Book app
- App Chat app
- App Chat app
- App Management app
- App Management app
- App Management app
- App Management app
- App Management app
- App Management app
- App Management app
- App Management app
- App Management app
- App Management app
- App Management app
- App Management app
- App Management app
- App Management app
- App Management app
- App Payments app
- App Payments app
- App Payments app
- App Payments app
- App Payments app
- App Payments app
- App Payments app
- App Payments app
- App Student app
- App Student app
- App Student app
- App Student app
- App Student app
- App Teacher app
- App Tutor app
- App Tutor app
- App User app
- App User app
- App User app
- App User app
- App User app
- App User app
- App User app
- App User app
- App User app
- App User app
- App User app
- App User app
- Requirements

## God Nodes (most connected - your core abstractions)
1. `Student` - 150 edges
2. `Teacher` - 62 edges
3. `Subject` - 58 edges
4. `Topic` - 52 edges
5. `Question` - 48 edges
6. `TopicProgress` - 42 edges
7. `Chapter` - 39 edges
8. `StudentScore` - 38 edges
9. `User` - 35 edges
10. `Tutor` - 35 edges

## Surprising Connections (you probably didn't know these)
- `get_logs()` --uses--> `HelpRequestMessageLog`  [INFERRED]
  helped_bot.py → django_app/app_student/models.py
- `send_question_to_telegram()` --uses--> `HelpRequestMessageLog`  [INFERRED]
  helped_bot.py → django_app/app_student/models.py
- `update_message_log()` --uses--> `HelpRequestMessageLog`  [INFERRED]
  helped_bot.py → django_app/app_student/models.py
- `update_chapter_orders()` --uses--> `Subject`  [INFERRED]
  orderindex.py → django_app/app_user/models.py
- `Django REST Framework (djangorestframework)` --conceptually_related_to--> `Multi-Akkount API (Telegram-style Multi-Account API)`  [INFERRED]
  requirements.txt → graphify-out/converted/api_85223c56.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **1-daraja Worksheet Content Across Formats** — graphify_out_converted_6_2de5165d_1_daraja_worksheet, savol_1_daraja_worksheet, testdoc_out_1_daraja_worksheet, testdoc_savol_1_daraja_worksheet [INFERRED 0.85]
- **IQMath Chat Frontend Authentication Flow** — graphify_out_converted_api_85223c56_access_token, student_chat_student_chat_ui, teacher_chat_teacher_chat_ui, shablon_teacher_chat_template [INFERRED 0.75]
- **IQMath Question Bank Schema Family** — graphify_out_converted_choice_d9f0c1ab_choice_question_schema, graphify_out_converted_shablon_6a78ad60_shablon_template, graphify_out_converted_composite_75d61e85_composite_question_schema, graphify_out_converted_savol_48e1ceed_savol_question_data [INFERRED 0.75]

## Communities (206 total, 84 thin omitted)

### Community 0 - "App Student app"
Cohesion: 0.05
Nodes (32): collections, get_daily_coin_limit(), get_or_create_daily_log(), get_today_coin_count(), StudentScoreLog orqali bugungi yig'ilgan tanga sonini olish (mahalliy vaqt…, Bugungi StudentDailyCoinLog ni olish yoki yangi yaratish (mahalliy vaqt…, Kunlik tanga chegrasini admin sozlamasidan olish. Yo'q bo'lsa 10 qaytaradi., Har bir o"quvchi uchun kunlik yig'ilgan tanga soni." Admin panelda kun bo"yicha… (+24 more)

### Community 1 - "App Student app"
Cohesion: 0.03
Nodes (30): Migration, Migration, Migration, Migration, Migration, Migration, Migration, Migration (+22 more)

### Community 2 - "App Management app"
Cohesion: 0.04
Nodes (29): Migration, Migration, Migration, Migration, Migration, Migration, Migration, Migration (+21 more)

### Community 3 - "App Unversial View app"
Cohesion: 0.06
Nodes (28): Coupon_Tutor_Student, ReferralAndCouponSettings, Meta, APIView, Singleton model — tizimda faqat 1 ta yozuv bo'ladi. GET…, ReferralAndCouponSettingsSerializer, ReferralCouponSettingsCRUDAPIView, CouponSerializer (+20 more)

### Community 4 - "App Student - View"
Cohesion: 0.09
Nodes (25): Diagnost_Student, StudentScoreLog, ChapterTopicsAPIView, ParentStudentDiagnosticHistoryAPIView, APIView, StudentDiagnosticHistoryAPIView, StudentDiagnostSubjectsAPIView, SubjectChaptersAPIView (+17 more)

### Community 5 - "App User app"
Cohesion: 0.07
Nodes (24): AbstractUser, LogEntryAdmin, ParentAdmin, register, ReferralAdmin, StudentAdmin, TeacherAdmin, TutorAdmin (+16 more)

### Community 6 - "App Teacher app"
Cohesion: 0.09
Nodes (28): base64, bs4, Question, ChoiceSerializer, CompositeSubQuestionSerializer, QuestionSerializer, RetrieveAPIView, TeacherTopicHelpRequestDetailAPIView (+20 more)

### Community 7 - "App Management - VIEW"
Cohesion: 0.08
Nodes (19): Category, CertificateSettings, Coupon, DailyCoinSettings, Elon, Meta, Tag, ElonSerializer (+11 more)

### Community 8 - "App Student app"
Cohesion: 0.09
Nodes (28): Subscription, Meta, StudentCouponTransaction, StudentReferral, StudentReferralTransaction, StudentScore, TopicProgress, DiagnostSubjectSerializer (+20 more)

### Community 9 - "App User app"
Cohesion: 0.06
Nodes (29): AddChildRequestAPIView, AdminResetUserPasswordAPIView, BlockUserAPIView, ConfirmChildAPIView, ForgotPasswordView, LogoutAPIView, LogoutDeviceAPIView, APIView (+21 more)

### Community 10 - "App Management app"
Cohesion: 0.07
Nodes (26): BannerAdmin, CategoryAdmin, CertificateSettingsAdmin, ConversionRateAdmin, Coupon_Tutor_StudentAdmin, DailyCoinSettingsAdmin, ElonAdmin, FAQAdmin (+18 more)

### Community 11 - "App Tutor app"
Cohesion: 0.11
Nodes (26): _detail_context(), APIView, O'qituvchi (tutor) guruhlari: yaratish, ro'yxat, tahrirlash, o'chirish va…, POST /api/v1/tutor/tutor/groups/<pk>/students/ - {student_ids: []} guruhga…, GET /api/v1/tutor/tutor/my-students/ - tutor promo/kupon orqali qo'shgan…, group_id/group_name ni ortiqcha so'rovsiz olish uchun tutor guruhlarini…, Guruh queryset'i — o'quvchilari va ularning guruh nomlari bilan birga., TutorGroupDetailSerializer uchun kontekst (tutor + o'rtacha ball). (+18 more)

### Community 12 - "App Tutor app"
Cohesion: 0.09
Nodes (28): get_student(), IsStudent, IsTutor, BasePermission, Faqat tutor profiliga ega foydalanuvchi (admin/superadmin ham ko'ra oladi)., Faqat o'quvchi profiliga ega foydalanuvchi., Request egasining o'quvchi profili yoki None., _class_uz() (+20 more)

### Community 13 - "App Payments app"
Cohesion: 0.12
Nodes (24): dateutil_relativedelta, CouponUsage_Tutor_Student, Payment, PaymentSerializer, PaymentTeacherSerializer, expire_pending_payments_task(), shared_task, Har ishga tushganda timeoutdan oshgan pending paymentlarni failed qiladi. (+16 more)

### Community 14 - "App User - VIEW"
Cohesion: 0.08
Nodes (21): Ushbu metod foydalanuvchi yana SMS kod olishi mumkinligini tekshiradi. Agar SMS…, Foydalanuvchiga SMS yuborishdan oldin ushbu metod orqali urinishni ro'yxatga…, UserSMSAttempt, send_login_parol_resend_email(), send_sms(), send_sms_resend(), send_verification_email(), ChangePasswordView (+13 more)

### Community 15 - "App Student - View"
Cohesion: 0.09
Nodes (17): SubjectCategoryDetailSerializer, APIView, QuickMathQuestionAPIView, SubmitQuickMathAnswerAPIView, APIView, Oy ichidagi hafta raqamini hisoblaydi, Boshqa loyihadagi API'lar bilan bir xil pagination pattern…, StudentRatingAPIView (+9 more)

### Community 16 - "App Battle app"
Cohesion: 0.12
Nodes (27): channels_generic_websocket, advance_to_next_question(), _arm_question_timers(), _avg_seconds_on_correct(), _award_battle_win_reward(), _bot_answer_payload(), bot_answer_question(), finish_battle() (+19 more)

### Community 17 - "App Student app"
Cohesion: 0.10
Nodes (20): ChapterProgress, TopicHelpRequestIndependent, CheckChoiceAnswerSerializer, CheckCompositeAnswerSerializer, CheckTextAnswerSerializer, ChoiceSerializer, CompositeSubQuestionSerializer, Meta (+12 more)

### Community 18 - "App Battle app"
Cohesion: 0.14
Nodes (21): BattleEloLog, level_for_elo(), level_progress(), (floor, ceiling, elo_into_band, band_width, pct_to_next) for the level-progress…, Never emit anything that reveals bot-ness — name/elo/level must be…, RoomCreateSerializer, RoomJoinSerializer, serialize_participant() (+13 more)

### Community 19 - "App Teacher app"
Cohesion: 0.09
Nodes (25): ChapterAdmin, ChoiceAdmin, ChoiceInline, CompositeSubQuestionAdmin, CompositeSubQuestionInline, GeneratedChoiceOpenAiAdmin, GeneratedChoiceOpenAiInline, GeneratedQuestionOpenAiAdmin (+17 more)

### Community 20 - "App Teacher app"
Cohesion: 0.11
Nodes (24): GeneratedQuestionOpenAi, TeacherRewardLog, GeneratedChoiceOpenAiSerializer, GeneratedQuestionOpenAiSerializer, GeneratedSubQuestionOpenAiSerializer, GroupSerializer_DETAIL, Meta, OpenAIChoiceSerializer (+16 more)

### Community 21 - "App Battle app"
Cohesion: 0.11
Nodes (20): BattleBotDifficultyAdmin, BattleBotIdentityAdmin, BattleEloLogAdmin, BattleParticipantInline, BattleRatingAdmin, BattleRoomAdmin, register, bot_elo_before() (+12 more)

### Community 22 - "App Management app"
Cohesion: 0.11
Nodes (19): UploadedFile, MathematicianListSerializer, BannerListView, DeleteFileAPIView, ElonDetailAPIView, ElonListAPIView, FAQListView, FullStatisticsAPIView (+11 more)

### Community 23 - "App Tutor app"
Cohesion: 0.15
Nodes (19): Meta, TutorCouponTransaction, TutorReferralTransaction, TutorWithdrawal, WithdrawalLimitSettings, TutorCouponTransactionSerializer, TutorReferralTransactionSerializer, TutorWithdrawalSerializer (+11 more)

### Community 24 - "App Student app"
Cohesion: 0.09
Nodes (21): d_ishxona_iq_math_orginal_iq_math_orginal_django_app_app_payments_models_py, ChapterProgressAdmin, ConversionHistoryAdmin, display, register, TranslationAdmin, StudentDailyCoinLogAdmin, StudentScoreAdmin (+13 more)

### Community 25 - "App User app"
Cohesion: 0.09
Nodes (21): datetime, Device, ParentLoginHistory, TutorLoginHistory, AddAccountSerializer, create_user_tokens(), AddAccountAPIView, SwitchAccountAPIView (+13 more)

### Community 26 - "App Book app"
Cohesion: 0.07
Nodes (19): AppBattleConfig, AppConfig, AppBookConfig, AppConfig, AppChatConfig, AppConfig, AppManagementConfig, AppConfig (+11 more)

### Community 27 - "App Student - View"
Cohesion: 0.25
Nodes (9): django_contrib_contenttypes_models, django_shortcuts, django_template_loader, django_utils, rest_framework, rest_framework_pagination, rest_framework_permissions, rest_framework_response (+1 more)

### Community 28 - "App Student - View"
Cohesion: 0.11
Nodes (17): ProductExchange, Student ↔ Student so"m o'tkazish logi." - is_confirmed=False → OTP kutilmoqda…, SomTransferLog, ProductExchangeConfirmAPIView, ProductExchangeListView, ProductExchangeView, APIView, APIView (+9 more)

### Community 29 - "App Teacher - View"
Cohesion: 0.14
Nodes (13): Group, GroupSerializer, AddStudentsToGroupAPIView, GroupCreateAPIView, GroupListAPIView, _is_superadmin(), IsSuperAdmin, IsTeacherOrSuperAdmin (+5 more)

### Community 30 - "App Student app"
Cohesion: 0.11
Nodes (24): advanced_math_check(), clean_latex(), clean_student_answers_list(), compare_answers(), decimal_comma_to_dot(), detect_variables(), html_to_math_text(), insert_multiplication() (+16 more)

### Community 31 - "App Battle app"
Cohesion: 0.15
Nodes (9): BattleFixtureMixin, EngineFullMatchTests, GradingTests, MatchmakingTests, PlacementEloRevealTests, Covers the product spec directly: no visible ELO during the first 10 matches,…, patch, TestCase (+1 more)

### Community 32 - "App Management app"
Cohesion: 0.12
Nodes (18): Banner, BannerSerializer, auto_delete_banner_image_on_change(), auto_delete_banner_image_on_delete(), auto_delete_system_file_on_change(), auto_delete_system_file_on_delete(), elon_send_notification(), elon_track_notification_status() (+10 more)

### Community 33 - "App Chat app"
Cohesion: 0.12
Nodes (14): channels_db, channels_routing, ASGI config for config project. It exposes the ASGI callable as a module-level…, django, JwtAuthMiddleware, JwtAuthMiddlewareStack(), django_contrib_auth_models, django_core_asgi (+6 more)

### Community 34 - "App Payments - VIEW"
Cohesion: 0.21
Nodes (10): SubscriptionBenefit, SubscriptionCategory, SubscriptionBenefitStatusSerializer, Meta, SubscriptionBenefitCreateSerializer, SubscriptionBenefitReadSerializer, SubscriptionCategoryCreateSerializer, SubscriptionCategoryReadSerializer (+2 more)

### Community 35 - "App Tutor app"
Cohesion: 0.12
Nodes (19): get_tutor_students(), Tutorga tegishli o'quvchilar queryset'i., _build_student_rows(), _group_map(), _percent(), APIView, student_id -> {id, name} (tutorning qaysi guruhida ekanligi)., GET /api/v1/tutor/tutor/results/students/ - barcha o'quvchilarning natijalari… (+11 more)

### Community 36 - "App User app"
Cohesion: 0.12
Nodes (17): Class, UserSession, check_login_attempts(), Class_Serializer, Meta, ParentCreateSerializer, Login urinishlarini tekshiradi va bloklash uchun hisoblaydi., Agar foydalanuvchi to'g'ri kirsa, urinishlar sonini 0 ga tushiramiz. (+9 more)

### Community 37 - "App User app"
Cohesion: 0.11
Nodes (18): celery_schedules, book_created_notification(), receiver, _build_response(), get_next_topic_for_student(), Studentning keyingi o'rganishi kerak bo'lgan mavzusini qaytaradi. `subject`…, shared_task, send_daily_topic_notifications() (+10 more)

### Community 38 - "App Management app"
Cohesion: 0.09
Nodes (12): ckeditor_fields, Migration, Migration, Migration, Migration, Migration, Migration, Migration (+4 more)

### Community 39 - "App Teacher - Commands"
Cohesion: 0.10
Nodes (14): Command, BaseCommand, django_core_management_base, docx, docx_enum_text, docx_oxml, docx_oxml_ns, docx_shared (+6 more)

### Community 40 - "App Tutor app"
Cohesion: 0.11
Nodes (16): get_tutor_student_ids(), O'qituvchi (tutor) modullari uchun umumiy yordamchi funksiyalar., Tutor o'z promo havolasi yoki kuponi orqali qo'shgan o'quvchilarning id'lari.…, O'qituvchi (tutor) o'z promo/referal havolasi orqali qo'shgan o'quvchilarini…, TutorGroup, _collect_student_sets(), _parse_period(), _period_start() (+8 more)

### Community 41 - "App User app"
Cohesion: 0.13
Nodes (8): Teacher, StudentSerializer, TeacherSerializer, TeacherVerifySmsCodeSerializer, POST: { "phone": 998911234567, "telegram_id": 454465465 } phone bo"lsa…, TeacherVerifySmsCodeAPIView, TelegramIDCheckAPIView, UpdateTelegramIDAPIView

### Community 42 - "App Student - View"
Cohesion: 0.13
Nodes (11): PageNumberPagination, StandardResultsSetPagination, StudentLoginHistorySerializer, ListAPIView, StudentLoginHistoryListAPIView, APIView, _serialize_diagnost(), SuperAdminDiagnostCRUDAPIView (+3 more)

### Community 43 - "App Battle app"
Cohesion: 0.18
Nodes (17): _advisory_lock_key(), cancel_room(), create_participant_for_student(), find_or_create_room(), join_room_by_code(), _new_room(), _random_bot_delay(), Room creation / matchmaking. The only place that decides *whether* two students… (+9 more)

### Community 44 - "App User app"
Cohesion: 0.15
Nodes (14): delete_pending_registration(), _get_client(), get_pending_registration(), _key(), Ro"yxatdan o'tish jarayoni uchun Redis yordamchi moduli." Celery (db=0) va…, Ro"yxatdan o'tish ma'lumotlarini Redisga saqlaydi." TTL: REGISTRATION_REDIS_TTL…, Redisdan ro'yxatdan o'tish ma'lumotlarini oladi. Topilmasa None qaytaradi., Redis kalitini o'chiradi (SMS tasdiqlangandan keyin). (+6 more)

### Community 45 - "App Chat app"
Cohesion: 0.11
Nodes (10): Migration, Migration, Migration, Migration, Migration, Migration, Migration, Migration (+2 more)

### Community 46 - "App Management - VIEW"
Cohesion: 0.17
Nodes (8): SystemSettings, IsTeacherOrSuperAdmin, BasePermission, Teacher va SuperAdmin rollari kira oladi, SystemSettingsSerializer, APIView, Singleton model - tizimda faqat 1 ta SystemSettings yozuvi bo'ladi. GET…, SystemSettingsCRUDAPIView

### Community 47 - "Converted"
Cohesion: 0.18
Nodes (19): Access Token (JWT Bearer Auth), POST /user/auth/add-account/ Endpoint, IQMath API Base URL (api.iqmath.uz), Multi-Akkount API (Telegram-style Multi-Account API), Parent-Child Linking via SMS Verification, POST /user/auth/remove-account/ Endpoint, GET /user/auth/sessions/ Endpoint, POST /user/auth/switch-account/ Endpoint (+11 more)

### Community 48 - "Helped Bot"
Cohesion: 0.20
Nodes (18): ask_for_phone(), get_logs(), get_student_telegram_id(), handle_callback(), handle_contact(), handle_message(), main(), DEFAULT_TYPE (+10 more)

### Community 49 - "App Book app"
Cohesion: 0.20
Nodes (10): Book, BookPayment, BookPurchase, Category, Meta, Kitob uchun onlayn (Multicard) to'lov. Foydalanuvchining tanga/ball/so'm…, Tag, calc_book_prices() (+2 more)

### Community 50 - "App Management - VIEW"
Cohesion: 0.17
Nodes (9): Product, ProductSerializer, IsSuperAdmin, Meta, ProductCRUDAPIView, ProductWriteSerializer, APIView, BasePermission (+1 more)

### Community 51 - "App User app"
Cohesion: 0.14
Nodes (11): All_Role_ListView, DeleteStudentProfileAPIView, escape_uri_path(), ParentDetailAPIView, APIView, Fayl nomini URLga moslashtirish, Foydalanuvchi roliga qarab profil ma'lumotlarini olish, Rolni ko'rinishli qilib qaytarish (+3 more)

### Community 52 - "Bot Telegram"
Cohesion: 0.24
Nodes (12): asyncio, answer_help_request(), handle_media_answer(), handle_teacher_callback(), DEFAULT_TYPE, Update, receive_answer_text(), setup_handlers() (+4 more)

### Community 53 - "App Book app"
Cohesion: 0.16
Nodes (9): BookInitiatePaymentAPIView, BookPurchaseAPIView, MyBookPaymentsAPIView, MyPurchasedBooksAPIView, APIView, GET /book/my-payments/ → o'z kitob to'lovlari ro'yxati GET /book/my-…, POST /book/purchase/ Body: { "book_id": 1, "payment_method": "coin" }…, GET /book/my-purchases/ → barcha sotib olingan kitoblar GET /book/my-… (+1 more)

### Community 54 - "App Teacher - View"
Cohesion: 0.14
Nodes (10): GetTelegramIDFromHelpRequestAPIView, APIView, PageNumberPagination, Qo'ng'iroqcha uchun xabarlar soni, statistikasi va ularni Ko'rildi deb belgilash, StandardResultsSetPagination, TeacherCommitToHelpRequestAPIView, TeacherHelpRequestNotificationAPIView, TeacherTopicHelpRequestDeleteAPIView (+2 more)

### Community 55 - "App Chat app"
Cohesion: 0.19
Nodes (7): ChatConsumer, AsyncWebsocketConsumer, Message, create_message(), user_in_conversation(), StudentSupportChatMessageAPIView, django_core_exceptions

### Community 56 - "App Chat app"
Cohesion: 0.20
Nodes (10): ConversationAssignment, IsTeacher, BasePermission, ConversationTransferSerializer, Meta, TeacherListSerializer, broadcast_chat_message(), ConversationTransferAPIView (+2 more)

### Community 57 - "App Chat app"
Cohesion: 0.16
Nodes (7): APIView, POST { "teacher_id": 5 } → shu teacher qancha chatga javob bergan…, ReadMessageAPIView, SuperAdminTeachersClosedChatsStatsAPIView, TeacherClosedChatsStatsAPIView, TeacherStatsByIdAPIView, TotalUnreadChatsAPIView

### Community 58 - "App Management - VIEW"
Cohesion: 0.17
Nodes (8): CategorySerializer, DailyCoinSettingsSerializer, MathematicianDetailSerializer, Meta, CategoryCRUDAPIView, APIView, DailyCoinSettingsCRUDAPIView, APIView

### Community 59 - "App Student - View"
Cohesion: 0.16
Nodes (10): ConversionHistory, _build_qs(), ConversionHistoryCRUDAPIView, ConversionHistoryPagination, APIView, PageNumberPagination, _serialize_conversion(), ConvertView (+2 more)

### Community 60 - "App Student - View"
Cohesion: 0.15
Nodes (11): _build_qs(), IsSuperAdmin, MyScoreLogAPIView, APIView, BasePermission, PageNumberPagination, GET /student/my-score-log/ → o'zining loglari GET /student/my-score-…, GET /student/score-log/ → barcha loglar (superadmin/admin) GET /student/score-… (+3 more)

### Community 61 - "App Battle app"
Cohesion: 0.13
Nodes (5): asgiref_sync, channels_layers, BattleConsumer, AsyncWebsocketConsumer, group_name()

### Community 62 - "Bot Telegram"
Cohesion: 0.24
Nodes (14): get_logs(), get_student_telegram_id(), handle_callback(), handle_message(), main(), DEFAULT_TYPE, sync_to_async, Update (+6 more)

### Community 63 - "App Chat app"
Cohesion: 0.20
Nodes (6): ConversationSerializer, MessageSerializer, ConversationMessagesAPIView, CreateDirectChatAPIView, RequestCloseConversationAPIView, SendMessageAPIView

### Community 64 - "App Management - VIEW"
Cohesion: 0.22
Nodes (8): Mathematician, IsSuperAdmin, MathematicianCRUDAPIView, MathematicianReadSerializer, MathematicianWriteSerializer, Meta, APIView, BasePermission

### Community 65 - "App Management - VIEW"
Cohesion: 0.19
Nodes (7): Maksimal hajm (baytlarda), UploadSetting, UploadSettingSerializer, IsTeacherOrSuperAdmin, APIView, BasePermission, UploadSettingCRUDAPIView

### Community 66 - "App Payments - VIEW"
Cohesion: 0.19
Nodes (7): Meta, SubscriptionPlanCREATESerializer, SubscriptionREADPlanSerializer, IsSuperAdmin, APIView, BasePermission, SubscriptionPlanCRUDAPIView

### Community 67 - "App Tutor app"
Cohesion: 0.21
Nodes (7): IsSuperAdminOrAdmin, APIView, BasePermission, _serialize(), _validate_amounts(), WithdrawalLimitSettingsCRUDAPIView, rest_framework_routers

### Community 68 - "App Chat app"
Cohesion: 0.24
Nodes (6): ConversationRating, ConfirmCloseAndRateSerializer, ConversationMetaMixin, ConversationRatingSerializer, get_user_display_name(), ConfirmCloseAndRateAPIView

### Community 69 - "App Student - View"
Cohesion: 0.18
Nodes (12): _build_overlay(), CertificateDownloadAPIView, _draw_certificate(), _fit_font_size(), APIView, Matn berilgan kenglikka sig'maguncha shrift hajmini kichraytiradi., Shablon ustiga yoziladigan matnlarni o'z ichiga olgan shaffof PDF qatlam…, Tayyor shablon (Media/certificate/certificate_template.pdf) ustiga student… (+4 more)

### Community 70 - "App User app"
Cohesion: 0.15
Nodes (3): StudentSerializerParent, ParentChildrenListAPIView, Ota-ona qo"shgan va tasdiqlangan farzandlar ro'yxati"

### Community 71 - "App Book app"
Cohesion: 0.19
Nodes (5): TagSerializer, IsSuperAdmin, BasePermission, GET /book/tags/ → list POST /book/tags/ → create (superadmin) GET…, TagCRUDAPIView

### Community 72 - "App Management - VIEW"
Cohesion: 0.23
Nodes (6): FAQ, FAQSerializer, FAQCRUDAPIView, IsSuperAdmin, APIView, BasePermission

### Community 73 - "App Management - VIEW"
Cohesion: 0.23
Nodes (6): Motivation, MotivationSerializer, IsSuperAdmin, MotivationCRUDAPIView, APIView, BasePermission

### Community 74 - "App Management - VIEW"
Cohesion: 0.23
Nodes (6): SolutionStatus, SolutionStatusSerializer, IsTeacherOrSuperAdmin, APIView, BasePermission, SolutionStatusCRUDAPIView

### Community 75 - "App Student app"
Cohesion: 0.19
Nodes (5): Topic_STUDENT_ID_Serializer, TopicSerializer, Teacher/Admin -> student_id talab qilinmaydi Student -> student_id yuborishi…, TopicListByChapter_STUDENT_ID_APIView, TopicListByChapterAPIView

### Community 76 - "App Teacher app"
Cohesion: 0.23
Nodes (11): TranslationOptions, TopicHelpRequestIndependentTranslationOptions, ChapterTranslationOptions, ChoiceTranslationOptions, CompositeSubQuestionTranslationOptions, TranslationOptions, QuestionTranslationOptions, Subject_CategoryTranslationOptions (+3 more)

### Community 77 - "Bot Telegram"
Cohesion: 0.24
Nodes (5): BotManager, main(), DEFAULT_TYPE, Update, O'qituvchilarga savolni yuborish funksiyasi

### Community 78 - "App Tutor app"
Cohesion: 0.24
Nodes (5): Referral_Tutor_Student, ReferralCreateSerializer, ReferralSerializer, A-Z va 0-9 dan iborat unikal referal kodi yaratish., TutorReferralViewSet

### Community 79 - "App Management - VIEW"
Cohesion: 0.21
Nodes (7): ConversionRateCRUDAPIView, ConversionRateSerializer, IsSuperAdmin, Meta, APIView, BasePermission, Singleton model — tizimda faqat 1 ta yozuv bo'ladi. GET…

### Community 80 - "Converted"
Cohesion: 0.18
Nodes (12): Arifmetik progressiya (Arithmetic Progression), f(x)=x^2-3x+1=1 Equation Question, f(x)=x^2-x+1, f(0) Question, Geometrik progressiya (Geometric Progression), IX Sinf (Grade 9) Math Multiple-Choice Test Bank, Logarifmik tenglama va tengsizliklar (Logarithmic Equations/Inequalities), Murakkab va teskari funksiya (Composite & Inverse Function), Trigonometrik ayniyatlar (Trigonometric Identities) (+4 more)

### Community 81 - "App Management app"
Cohesion: 0.18
Nodes (4): APITransactionTestCase, SystemSettingsCRUDAPITestCase, rest_framework_test, types

### Community 82 - "App Management - VIEW"
Cohesion: 0.33
Nodes (5): AndroidVersion, AndroidVersionSerializer, AndroidVersionAPIView, APIView, BAZADA FAQAT BITTA YOZUV BO'LADI

### Community 83 - "App Payments - VIEW"
Cohesion: 0.24
Nodes (6): Meta, SubscriptionSetting, Meta, APIView, SubscriptionSettingCRUDAPIView, SubscriptionSettingSerializer

### Community 84 - "App Payments - VIEW"
Cohesion: 0.31
Nodes (5): SubscriptionCreateUpdateSerializer, SubscriptionReadSerializer, MySubscriptionAPIView, APIView, SubscriptionCRUDAPIView

### Community 85 - "App Book app"
Cohesion: 0.31
Nodes (7): BookAdmin, BookPaymentAdmin, BookPurchaseAdmin, CategoryAdmin, OfflineBookOrderAdmin, register, TagAdmin

### Community 86 - "App Chat app"
Cohesion: 0.27
Nodes (5): ConversationListSerializer, get_chat_queryset(), get_chat_queryset_for_user(), LatestConversationAPIView, UniversalChatsAPIView

### Community 87 - "App Payments app"
Cohesion: 0.36
Nodes (9): PaymentAdmin, register, TranslationAdmin, SubscriptionAdmin, SubscriptionBenefitAdmin, SubscriptionCategoryAdmin, SubscriptionPlanAdmin, SubscriptionSettingAdmin (+1 more)

### Community 88 - "App Payments app"
Cohesion: 0.24
Nodes (3): SubscriptionPlan, SubscriptionPlanSerializer, SubscriptionPlanListAPIView

### Community 89 - "App Teacher - View"
Cohesion: 0.20
Nodes (6): APIView, O'qituvchi uchun javobsiz va ko'rilmagan misollar sonini qaytaradi, Barcha 'pending' misollarni 'ko'rildi' deb belgilaydi, TeacherAnswerUnsolvedQuestionView, TeacherNotificationsAPIView, TeacherUnsolvedQuestionReportListView

### Community 90 - "App Chat app"
Cohesion: 0.28
Nodes (5): CreateAPIView, ConversationParticipant, increase_unread_count(), receiver, TopicHelpRequestCreateView

### Community 91 - "App Battle app"
Cohesion: 0.25
Nodes (8): compute_elo_delta(), expected_score(), match_outcome(), performance_score(), Faceit-style ELO with a performance multiplier. Pure functions only (no DB…, Blends accuracy (0.7) and speed-on-correct-answers only (0.3), so fast wrong…, More correct answers wins; ties broken by lower total answer time; still tied =…, `result` is 'win'/'loss'/'draw' from self's perspective. A true coin-flip draw…

### Community 92 - "App Battle app"
Cohesion: 0.25
Nodes (3): BattleRating, Placement matches (the student's first 10) never move a visible ELO number —…, Post-placement matches only — normal incremental ELO.

### Community 93 - "App Book app"
Cohesion: 0.28
Nodes (4): OfflineBookOrder, Oflayn kitob buyurtmasi — yetkazib berish holati shu yerda saqlanadi., AdminOfflineOrderAPIView, GET /book/offline-orders/ → barcha offline buyurtmalar (admin/superadmin) GET…

### Community 94 - "App Book app"
Cohesion: 0.39
Nodes (5): BookReadSerializer, BookWriteSerializer, Meta, BookCRUDAPIView, GET /book/books/ → list (filter: ?category=<id>, ?status=active, ?tag=<id>)…

### Community 95 - "App Chat app"
Cohesion: 0.31
Nodes (4): Conversation, MessageReceipt, Meta, TypingIndicator

### Community 96 - "App Tutor app"
Cohesion: 0.31
Nodes (4): CouponCreateSerializer, CouponSerializer, A-Z va 0-9 dan iborat unikal kupon kodi yaratish., TutorCouponViewSet

### Community 97 - "App User app"
Cohesion: 0.28
Nodes (5): LoginSerializer, LoginAPIView, Foydalanuvchining IP-manzilini olish, Foydalanuvchining qurilmasi haqida ma'lumot olish, TeacherLoginAPIView

### Community 98 - "App Battle app"
Cohesion: 0.25
Nodes (3): EloFormulaTests, Covers exactly the cases called out in the implementation plan's verification…, SimpleTestCase

### Community 99 - "App Management app"
Cohesion: 0.43
Nodes (7): ElonTranslationOptions, FAQTranslationOptions, MathematicianTranslationOptions, MotivationTranslationOptions, ProductTranslationOptions, TranslationOptions, SystemSettingsTranslationOptions

### Community 100 - "App Payments app"
Cohesion: 0.29
Nodes (4): PaymentSuperAdminSerializer, IsSuperAdmin, PaymentSuperAdminAPIView, BasePermission

### Community 101 - "App Payments app"
Cohesion: 0.25
Nodes (4): MD5 signature yaratish, Multicard dan kelgan to'lov callback ni qayta ishlash, Keshbeklarni taqsimlash, Subscriptionni yangilash/yaratish

### Community 102 - "App Teacher app"
Cohesion: 0.36
Nodes (4): MyChapterAddSerializer, MyChapterAddCreateView, MyChapterListView, Tizimga kirgan o'qituvchining barcha bo'limlarini olish

### Community 103 - "App Teacher app"
Cohesion: 0.36
Nodes (3): MyTopicAddSerializer, MyTopicAddCreateView, MyTopicListView

### Community 105 - "App Tutor app"
Cohesion: 0.36
Nodes (6): display, register, TutorCouponTransactionAdmin, TutorGroupAdmin, TutorGroupInvitationAdmin, WithdrawalLimitSettingsAdmin

### Community 106 - "App User app"
Cohesion: 0.25
Nodes (5): IsSuperAdminOnly, IsSuperAdminOrAdmin, DELETE /api/v1/auth/superadmin/delete-user/<user_id>/ Superadmin yoki admin…, SuperAdminDeleteUserAPIView, IsAuthenticated

### Community 107 - "App Book app"
Cohesion: 0.43
Nodes (3): CategorySerializer, CategoryCRUDAPIView, GET /book/categories/ → list POST /book/categories/ → create (superadmin) GET…

### Community 108 - "App Book app"
Cohesion: 0.33
Nodes (4): BookPaymentCallbackAPIView, expire_pending_book_payments(), Muddati o'tgan pending kitob to'lovlarini failed holatiga o'tkazadi., POST /book/payment-callback/ — Multicard callback. Imzo to'g'ri bo'lsa:…

### Community 110 - "App Management - VIEW"
Cohesion: 0.33
Nodes (3): LogEntryCRUDAPIView, APIView, _serialize()

### Community 111 - "App Student app"
Cohesion: 0.29
Nodes (5): advanced_math_check ni Django'siz sinash., django_core_management, importlib_util, io, sys

### Community 112 - "App Student - View"
Cohesion: 0.33
Nodes (4): APIView, UnsolvedQuestionCreateView, UnsolvedQuestionReportListView, UnsolvedQuestionReport

### Community 113 - "App Teacher - View"
Cohesion: 0.29
Nodes (4): APIView, 📌 oldindan kelgan ID larni ko'rildi deb belgilash, TeacherProductExchangeListAPIView, TeacherUpdateProductExchangeStatusAPIView

### Community 114 - "App Teacher - View"
Cohesion: 0.29
Nodes (5): _get_full_name(), APIView, POST /api/v1/teacher/fine/ Teacher yoki superadmin studentga jarima qo'yadi.…, _serialize_fine(), TeacherFineAPIView

### Community 116 - "App User app"
Cohesion: 0.38
Nodes (4): Barcha tekshiruvlarni yagona joyda bajarish, Foydalanuvchi ma'lumotlarini tekshirish, TeacherRegisterSerializer, RegisterTeacherAPIView

### Community 117 - "Testdoc"
Cohesion: 0.33
Nodes (6): flask, json, openai, route, index(), process_text()

### Community 119 - "Testdoc"
Cohesion: 0.47
Nodes (6): Kasrlarni bo'lish (Dividing Fractions) Question Bank, 1-daraja (Level 1) Fraction Arithmetic Worksheet, 1-daraja Worksheet (savol_uz/javob_uz labeled), Kasrlarni bo'lish (Dividing Fractions) - Clean LaTeX, 1-daraja Worksheet (LaTeX minipage table), 1-daraja Worksheet (savol_uz labeled, LaTeX)

### Community 121 - "App Book app"
Cohesion: 0.60
Nodes (4): BookTranslationOptions, CategoryTranslationOptions, TranslationOptions, TagTranslationOptions

### Community 122 - "App Payments app"
Cohesion: 0.60
Nodes (4): TranslationOptions, SubscriptionBenefitTranslationOptions, SubscriptionCategoryTranslationOptions, SubscriptionPlanTranslationOptions

### Community 123 - "App Teacher - View"
Cohesion: 0.40
Nodes (3): ChangeStudentPasswordAPIView, LoginAsStudentAPIView, APIView

### Community 124 - "App User app"
Cohesion: 0.40
Nodes (3): Profilning tasdiqlangan yoki tasdiqlanmagan holati, SMS kod tozalanganmi — ya'ni tasdiqlangan, UserAdmin

### Community 126 - "App Management - VIEW"
Cohesion: 0.50
Nodes (3): IsTeacherOrSuperAdmin, BasePermission, Faqat teacher va superadmin rollari kirishi mumkin

### Community 127 - "App Teacher - View"
Cohesion: 0.50
Nodes (3): APIView, URL: /teacher/online-duration/<int:teacher_id>/ teacher_id berilsa — shu…, TeacherOnlineDurationAPIView

## Ambiguous Edges - Review These
- `Telegram-style Multi-Account Switching Design` → `Telethon`  [AMBIGUOUS]
  requirements.txt · relation: conceptually_related_to

## Knowledge Gaps
- **150 isolated node(s):** `Migration`, `Migration`, `Migration`, `Migration`, `Migration` (+145 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 959 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **84 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Telegram-style Multi-Account Switching Design` and `Telethon`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `Student` connect `App Student - View` to `App Student app`, `App Unversial View app`, `App Student - View`, `App User app`, `App Management - VIEW`, `App Student app`, `App User app`, `App Tutor app`, `App Tutor app`, `App Payments app`, `App Student - View`, `App Battle app`, `App Student app`, `App Battle app`, `App Teacher app`, `App Battle app`, `App Management app`, `App Tutor app`, `App User app`, `App Student - View`, `App Teacher - View`, `App Battle app`, `App Payments - VIEW`, `App Tutor app`, `App User app`, `App Tutor app`, `App User app`, `App Student - View`, `App User app`, `App Chat app`, `App Student - View`, `App Battle app`, `App Chat app`, `App Student - View`, `App User app`, `App Student app`, `App Tutor app`, `App Battle app`, `App User app`, `App Student - View`, `App Teacher - View`, `App Tutor app`, `App Teacher - View`?**
  _High betweenness centrality (0.159) - this node is a cross-community bridge._
- **Why does `Teacher` connect `App User app` to `App Unversial View app`, `App Student - View`, `App User app`, `App Management - VIEW`, `App User app`, `App Student app`, `App Teacher app`, `App Management app`, `App User app`, `App Student - View`, `App Teacher - View`, `App User app`, `App Student - View`, `App Teacher - View`, `App Chat app`, `App Chat app`, `App Chat app`, `App Chat app`, `App Chat app`, `App Chat app`, `App User app`, `App Student - View`, `App User app`, `App Teacher - View`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `Subject` connect `App Student - View` to `App Student app`, `App User app`, `App Teacher app`, `App Student app`, `App User - VIEW`, `App Student - View`, `App Student app`, `App Battle app`, `App Teacher app`, `App Teacher app`, `App Battle app`, `App User app`, `App Student - View`, `App Battle app`, `App User app`, `App Battle app`, `App User app`, `App Teacher app`, `App Teacher app`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Are the 106 inferred relationships involving `Student` (e.g. with `BattleConsumer` and `BattleEloLog`) actually correct?**
  _`Student` has 106 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Migration`, `Migration`, `Migration` to the rest of the system?**
  _150 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `App Student app` be split into smaller, more focused modules?**
  _Cohesion score 0.053005464480874315 - nodes in this community are weakly interconnected._